from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ELEVATED_ROLES, WRITE_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.enums import (
    DomainEventType,
    PrivacyLevel,
    TaskScope,
    TaskStatus,
    TaskType,
    TaskVisibility,
)
from app.models import Article, Project, Task, TaskChecklistItem, User, WorkspaceMember
from app.schemas import (
    BoardMove,
    TaskChecklistItemCreate,
    TaskChecklistItemOut,
    TaskChecklistItemUpdate,
    TaskChecklistReorder,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.services.dispatch import dispatch_event
from app.services.events import emit_event
from app.services.notifications import notify_assignment
from app.services.realtime import make_event, publish_queued_events, queue_live_event

router = APIRouter(tags=["tasks"])


async def _assert_member(db: AsyncSession, workspace_id: str, user: User) -> WorkspaceMember:
    return await require_membership(workspace_id, db, user)


async def _load_task_with_access(db: AsyncSession, task_id: str, user: User) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.scope == TaskScope.PERSONAL:
        # EC-10 / AC-11: never reveal a foreign personal task.
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    else:
        await _assert_member(db, task.workspace_id, user)
    return task


async def _load_checklist_item_with_access(
    db: AsyncSession, item_id: str, user: User
) -> TaskChecklistItem:
    item = await db.get(TaskChecklistItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
    await _load_task_with_access(db, item.task_id, user)
    return item


def _queue_task_live_event(db: AsyncSession, type_: str, task: Task) -> None:
    payload = {"task_id": task.id, "status": task.status.value if task.status else None}
    if task.scope == TaskScope.PERSONAL:
        queue_live_event(db, make_event(type_, payload, target_user_ids=[task.owner_id]))
    else:
        queue_live_event(db, make_event(type_, payload, workspace_id=task.workspace_id))


async def _validate_workspace_assignees(
    db: AsyncSession, workspace_id: str, assignee_ids: list[str]
) -> list[str]:
    ids = list(dict.fromkeys(assignee_ids))
    if not ids:
        return []
    member_ids = set(
        (
            await db.scalars(
                select(WorkspaceMember.user_id).where(
                    WorkspaceMember.workspace_id == workspace_id
                )
            )
        ).all()
    )
    bad = [a for a in ids if a not in member_ids]
    if bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Исполнитель не состоит в лаборатории")
    return ids


@router.get("/tasks/{task_id}/checklist", response_model=list[TaskChecklistItemOut])
async def list_task_checklist(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _load_task_with_access(db, task_id, user)
    rows = await db.scalars(
        select(TaskChecklistItem)
        .where(TaskChecklistItem.task_id == task_id)
        .order_by(TaskChecklistItem.position.asc(), TaskChecklistItem.created_at.asc())
    )
    return rows.all()


@router.post(
    "/tasks/{task_id}/checklist",
    response_model=TaskChecklistItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_checklist_item(
    task_id: str,
    data: TaskChecklistItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _load_task_with_access(db, task_id, user)
    max_position = await db.scalar(
        select(func.max(TaskChecklistItem.position)).where(TaskChecklistItem.task_id == task_id)
    )
    item = TaskChecklistItem(
        task_id=task_id,
        created_by=user.id,
        title=data.title,
        kind=data.kind,
        position=int(max_position or 0) + 1,
    )
    db.add(item)
    _queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(item)
    return item


@router.patch("/task-checklist/{item_id}", response_model=TaskChecklistItemOut)
async def update_task_checklist_item(
    item_id: str,
    data: TaskChecklistItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _load_checklist_item_with_access(db, item_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    task = await db.get(Task, item.task_id)
    if task is not None:
        _queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(item)
    return item


@router.patch("/tasks/{task_id}/checklist/reorder", response_model=list[TaskChecklistItemOut])
async def reorder_task_checklist(
    task_id: str,
    data: TaskChecklistReorder,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _load_task_with_access(db, task_id, user)
    if data.order:
        rows = await db.scalars(
            select(TaskChecklistItem).where(TaskChecklistItem.task_id == task_id)
        )
        items = {item.id: item for item in rows.all()}
        for idx, item_id in enumerate(data.order):
            if item_id in items:
                items[item_id].position = idx
    _queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    rows = await db.scalars(
        select(TaskChecklistItem)
        .where(TaskChecklistItem.task_id == task_id)
        .order_by(TaskChecklistItem.position.asc(), TaskChecklistItem.created_at.asc())
    )
    return rows.all()


@router.delete("/task-checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_checklist_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _load_checklist_item_with_access(db, item_id, user)
    task = await db.get(Task, item.task_id)
    await db.delete(item)
    if task is not None:
        _queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    return None


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if data.scope == TaskScope.PERSONAL:
        # FR-TASK-5/6: owner = caller, private, no workspace required.
        task = Task(
            owner_id=user.id,
            created_by=user.id,
            assignee_id=user.id,
            title=data.title,
            description=data.description,
            scope=TaskScope.PERSONAL,
            visibility=TaskVisibility.PRIVATE,
            type=data.type if data.type != TaskType.OTHER else TaskType.PERSONAL,
            priority=data.priority,
            due_date=data.due_date,
        )
        db.add(task)
        await db.flush()
        _queue_task_live_event(db, "task.created", task)
        await db.commit()
        await publish_queued_events(db)
        await db.refresh(task)
        return task

    # ── team task: resolve workspace + visibility from scope ──
    workspace_id = data.workspace_id
    project_id = None
    article_id = None
    visibility = TaskVisibility.WORKSPACE

    if data.scope == TaskScope.PROJECT:
        if not data.project_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "project_id required for PROJECT scope")
        project = await db.get(Project, data.project_id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        project_id = project.id
        workspace_id = project.workspace_id
        visibility = TaskVisibility.PROJECT
    elif data.scope == TaskScope.ARTICLE:
        if not data.article_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "article_id required for ARTICLE scope")
        article = await db.get(Article, data.article_id)
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
        article_id = article.id
        workspace_id = article.workspace_id
        visibility = TaskVisibility.ARTICLE
    elif not workspace_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "workspace_id required for WORKSPACE scope")

    member = await _assert_member(db, workspace_id, user)
    if member.role not in WRITE_ROLES:  # FR-WS-5
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")

    # Собираем итоговый список исполнителей: assignee_ids (новый) ∪ assignee_id (старый).
    assignee_ids = await _validate_workspace_assignees(
        db,
        workspace_id,
        [*(data.assignee_ids or []), *([data.assignee_id] if data.assignee_id else [])],
    )

    task = Task(
        workspace_id=workspace_id,
        project_id=project_id,
        article_id=article_id,
        owner_id=user.id,
        created_by=user.id,
        assignee_id=assignee_ids[0] if assignee_ids else None,
        assignees=assignee_ids,
        title=data.title,
        description=data.description,
        scope=data.scope,
        visibility=visibility,
        type=data.type,
        priority=data.priority,
        due_date=data.due_date,
    )
    db.add(task)
    await db.flush()
    for aid in assignee_ids:  # FR-NOTIF-1 — уведомляем каждого исполнителя
        await notify_assignment(
            db,
            assignee_id=aid,
            actor_id=user.id,
            workspace_id=workspace_id,
            task_id=task.id,
            title=task.title,
        )
    _queue_task_live_event(db, "task.created", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _load_task_with_access(db, task_id, user)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _load_task_with_access(db, task_id, user)
    changes = data.model_dump(exclude_unset=True)
    prev_assignees = set(task.assignees or ([task.assignee_id] if task.assignee_id else []))
    # assignee_ids → синхронизируем основной assignee_id + список assignees
    assignment_changed = "assignee_ids" in changes or "assignee_id" in changes
    if task.scope == TaskScope.PERSONAL and assignment_changed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Личную задачу нельзя назначить другому")
    if "assignee_ids" in changes:
        ids = await _validate_workspace_assignees(db, task.workspace_id, changes.pop("assignee_ids") or [])
        task.assignees = ids
        task.assignee_id = ids[0] if ids else None
    elif "assignee_id" in changes:
        assignee_id = changes.pop("assignee_id")
        ids = await _validate_workspace_assignees(
            db, task.workspace_id, [assignee_id] if assignee_id else []
        )
        task.assignees = ids
        task.assignee_id = ids[0] if ids else None
    for field, value in changes.items():
        setattr(task, field, value)
    # отметка «кто выполнил» при ручной смене статуса на DONE
    if changes.get("status") == TaskStatus.DONE and task.completed_by is None:
        task.completed_by = user.id
        task.completed_at = datetime.now(timezone.utc)
    # Notify on a (re)assignment to a different team member (FR-NOTIF-1).
    if (
        task.scope != TaskScope.PERSONAL
        and assignment_changed
        and task.assignee_id
    ):
        new_assignees = set(task.assignees or ([task.assignee_id] if task.assignee_id else []))
        for assignee_id in new_assignees - prev_assignees:
            await notify_assignment(
                db,
                assignee_id=assignee_id,
                actor_id=user.id,
                workspace_id=task.workspace_id,
                task_id=task.id,
                title=task.title,
            )
    _queue_task_live_event(db, "task.updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(task)
    return task


def _can_complete(task: Task, member_role, user: User) -> bool:
    if task.scope == TaskScope.PERSONAL:
        return task.owner_id == user.id
    # FR-TASK-11/12: own task → ok; otherwise needs elevated role.
    if task.assignee_id == user.id or task.created_by == user.id:
        return True
    return member_role in ELEVATED_ROLES


@router.patch("/tasks/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    member_role = None
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    else:
        member = await _assert_member(db, task.workspace_id, user)
        member_role = member.role

    if not _can_complete(task, member_role, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot complete this task")

    # EC-1: completing an already-DONE task is a no-op (no duplicate reward).
    if task.status == TaskStatus.DONE:
        return task

    task.status = TaskStatus.DONE
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = user.id
    before_due = task.due_date is not None and date.today() <= task.due_date
    is_personal = task.scope == TaskScope.PERSONAL

    event = await emit_event(
        db,
        event_type=DomainEventType.TASK_COMPLETED,
        actor_id=user.id,
        entity_type="task",
        entity_id=task.id,
        workspace_id=task.workspace_id,
        privacy_level=PrivacyLevel.PRIVATE if is_personal else PrivacyLevel.WORKSPACE,
        payload={
            "scope": task.scope.value,
            "before_due": before_due,
            "beneficiary_id": task.assignee_id or user.id,
            # NFR-5 / AC-13: no title/description in payload for private events.
            "activity_text": None if is_personal else f"закрыл задачу «{task.title}»",
        },
    )
    event_id = event.id
    _queue_task_live_event(db, "task.updated", task)
    await db.commit()
    await publish_queued_events(db)
    await dispatch_event(event_id)
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}/reopen", response_model=TaskOut)
async def reopen_task(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    task = await _load_task_with_access(db, task_id, user)
    if task.status != TaskStatus.DONE:
        return task
    task.status = TaskStatus.TODO
    task.completed_at = None
    is_personal = task.scope == TaskScope.PERSONAL
    await emit_event(
        db,
        event_type=DomainEventType.TASK_REOPENED,
        actor_id=user.id,
        entity_type="task",
        entity_id=task.id,
        workspace_id=task.workspace_id,
        privacy_level=PrivacyLevel.PRIVATE if is_personal else PrivacyLevel.WORKSPACE,
        payload={"activity_text": None if is_personal else f"переоткрыл задачу «{task.title}»"},
    )
    _queue_task_live_event(db, "task.updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}/move", response_model=TaskOut)
async def move_task(
    task_id: str,
    data: BoardMove,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """DnD задачи: сменить статус (колонку) и/или порядок внутри списка.

    Перевод в DONE проходит через тот же reward-механизм, что и /complete.
    """
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    member_role = None
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    else:
        member = await _assert_member(db, task.workspace_id, user)
        member_role = member.role

    try:
        new_status = TaskStatus(data.status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown status")

    going_done = new_status == TaskStatus.DONE and task.status != TaskStatus.DONE
    leaving_done = task.status == TaskStatus.DONE and new_status != TaskStatus.DONE

    if going_done and not _can_complete(task, member_role, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot complete this task")

    # порядок внутри целевой колонки
    if data.order:
        for idx, tid in enumerate(data.order):
            t = await db.get(Task, tid)
            if t is not None:
                t.position = idx

    event_id = None
    if going_done:
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(timezone.utc)
        task.completed_by = user.id
        before_due = task.due_date is not None and date.today() <= task.due_date
        is_personal = task.scope == TaskScope.PERSONAL
        event = await emit_event(
            db,
            event_type=DomainEventType.TASK_COMPLETED,
            actor_id=user.id,
            entity_type="task",
            entity_id=task.id,
            workspace_id=task.workspace_id,
            privacy_level=PrivacyLevel.PRIVATE if is_personal else PrivacyLevel.WORKSPACE,
            payload={
                "scope": task.scope.value,
                "before_due": before_due,
                "beneficiary_id": task.assignee_id or user.id,
                "activity_text": None if is_personal else f"закрыл задачу «{task.title}»",
            },
        )
        event_id = event.id
    elif leaving_done:
        task.status = new_status
        task.completed_at = None
        task.completed_by = None
    else:
        task.status = new_status

    _queue_task_live_event(db, "task.moved", task)
    await db.commit()
    await publish_queued_events(db)
    if event_id:
        await dispatch_event(event_id)
    await db.refresh(task)
    return task


@router.get("/me/tasks", response_model=list[TaskOut])
async def my_tasks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Задачи, к которым причастен пользователь:
    #  - назначенные на него (assignee)
    #  - созданные им (owner) — включая проектные/командные без исполнителя
    rows = await db.scalars(
        select(Task)
        .where(
            or_(
                Task.assignee_id == user.id,
                Task.owner_id == user.id,
            )
        )
        .order_by(Task.created_at.desc())
    )
    return rows.all()


@router.get("/me/tasks/personal", response_model=list[TaskOut])
async def my_personal_tasks(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = await db.scalars(
        select(Task)
        .where(Task.scope == TaskScope.PERSONAL, Task.owner_id == user.id)
        .order_by(Task.created_at.desc())
    )
    return rows.all()
