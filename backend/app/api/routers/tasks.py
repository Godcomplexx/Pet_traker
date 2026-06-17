from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.enums import TaskScope, TaskStatus
from app.models import Task, User
from app.schemas import TaskCreate, TaskOut, TaskUpdate
from app.services.audit import diff_snapshots, record_audit, snapshot_fields
from app.services.notifications import notify_assignment
from app.services.realtime import publish_queued_events
from app.services.task_creation import create_task_for_user
from app.services.task_helpers import (
    TASK_AUDIT_FIELDS,
    load_task_with_access,
    queue_task_live_event,
    validate_workspace_assignees,
)

router = APIRouter(tags=["tasks"])


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await create_task_for_user(db, data, user)


@router.get("/tasks/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await load_task_with_access(db, task_id, user)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await load_task_with_access(db, task_id, user)
    changes = data.model_dump(exclude_unset=True)
    audit_before = snapshot_fields(task, TASK_AUDIT_FIELDS)
    prev_assignees = set(task.assignees or ([task.assignee_id] if task.assignee_id else []))
    assignment_changed = "assignee_ids" in changes or "assignee_id" in changes

    if task.scope == TaskScope.PERSONAL and assignment_changed:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Личную задачу нельзя назначить другому")
    await _apply_assignment_changes(db, task, changes)

    for field, value in changes.items():
        setattr(task, field, value)
    if changes.get("status") == TaskStatus.DONE and task.completed_by is None:
        task.completed_by = user.id
        task.completed_at = datetime.now(timezone.utc)

    await _notify_new_assignees(db, task, user, assignment_changed, prev_assignees)
    _record_update_audit(db, task, user, audit_before, assignment_changed)
    queue_task_live_event(db, "task.updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(task)
    return task


@router.get("/me/tasks", response_model=list[TaskOut])
async def my_tasks(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(
        select(Task)
        .where(or_(Task.assignee_id == user.id, Task.owner_id == user.id))
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


async def _apply_assignment_changes(db: AsyncSession, task: Task, changes: dict) -> None:
    if "assignee_ids" in changes:
        ids = await validate_workspace_assignees(db, task.workspace_id, changes.pop("assignee_ids") or [])
        task.assignees = ids
        task.assignee_id = ids[0] if ids else None
    elif "assignee_id" in changes:
        assignee_id = changes.pop("assignee_id")
        ids = await validate_workspace_assignees(
            db, task.workspace_id, [assignee_id] if assignee_id else []
        )
        task.assignees = ids
        task.assignee_id = ids[0] if ids else None


async def _notify_new_assignees(
    db: AsyncSession,
    task: Task,
    user: User,
    assignment_changed: bool,
    prev_assignees: set[str],
) -> None:
    if task.scope == TaskScope.PERSONAL or not assignment_changed or not task.assignee_id:
        return
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


def _record_update_audit(
    db: AsyncSession,
    task: Task,
    user: User,
    audit_before: dict,
    assignment_changed: bool,
) -> None:
    audit_after = snapshot_fields(task, TASK_AUDIT_FIELDS)
    before, after = diff_snapshots(audit_before, audit_after)
    if not before:
        return
    record_audit(
        db,
        workspace_id=task.workspace_id,
        actor_id=user.id,
        action="task.updated",
        entity_type="task",
        entity_id=task.id,
        before=before,
        after=after,
        target_user_id=task.assignee_id if assignment_changed else None,
        details={"changed_fields": list(after.keys())},
    )
