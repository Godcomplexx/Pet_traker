from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
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
from app.models import Article, Project, Task, User, WorkspaceMember
from app.schemas import TaskCreate, TaskOut, TaskUpdate
from app.services.dispatch import dispatch_event
from app.services.events import emit_event
from app.services.notifications import notify_assignment

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
        await db.commit()
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
    assignee_ids = list(dict.fromkeys([*(data.assignee_ids or []), *([data.assignee_id] if data.assignee_id else [])]))
    if assignee_ids:  # FR-TASK-7: каждый исполнитель должен быть участником лаборатории
        member_ids = set(
            (await db.scalars(
                select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
            )).all()
        )
        bad = [a for a in assignee_ids if a not in member_ids]
        if bad:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Исполнитель не состоит в лаборатории")

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
    await db.commit()
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
    prev_assignee = task.assignee_id
    # assignee_ids → синхронизируем основной assignee_id + список assignees
    if "assignee_ids" in changes:
        ids = changes.pop("assignee_ids") or []
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
        and "assignee_id" in changes
        and task.assignee_id
        and task.assignee_id != prev_assignee
    ):
        await notify_assignment(
            db,
            assignee_id=task.assignee_id,
            actor_id=user.id,
            workspace_id=task.workspace_id,
            task_id=task.id,
            title=task.title,
        )
    await db.commit()
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
    await db.commit()
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
    await db.commit()
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
