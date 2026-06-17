from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.enums import DomainEventType, PrivacyLevel, TaskScope, TaskStatus
from app.models import Task, User
from app.schemas import BoardMove, TaskOut
from app.services.audit import diff_snapshots, record_audit, snapshot_fields
from app.services.dispatch import dispatch_event
from app.services.events import emit_event
from app.services.realtime import publish_queued_events
from app.services.task_helpers import (
    TASK_AUDIT_FIELDS,
    assert_member,
    can_complete,
    load_task_with_access,
    queue_task_live_event,
)

router = APIRouter(tags=["tasks"])


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
        member = await assert_member(db, task.workspace_id, user)
        member_role = member.role

    if not can_complete(task, member_role, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot complete this task")
    if task.status == TaskStatus.DONE:
        return task

    audit_before = snapshot_fields(task, TASK_AUDIT_FIELDS)
    task.status = TaskStatus.DONE
    task.completed_at = datetime.now(timezone.utc)
    task.completed_by = user.id
    event_id = (await _emit_completed_event(db, task, user)).id
    _record_status_audit(db, task, user, audit_before, "task.completed")
    queue_task_live_event(db, "task.updated", task)
    await db.commit()
    await publish_queued_events(db)
    await dispatch_event(event_id)
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}/reopen", response_model=TaskOut)
async def reopen_task(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    task = await load_task_with_access(db, task_id, user)
    if task.status != TaskStatus.DONE:
        return task
    audit_before = snapshot_fields(task, TASK_AUDIT_FIELDS)
    task.status = TaskStatus.TODO
    task.completed_at = None
    task.completed_by = None
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
    _record_status_audit(db, task, user, audit_before, "task.reopened")
    queue_task_live_event(db, "task.updated", task)
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
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    member_role = await _member_role_for_task(db, task, user)
    try:
        new_status = TaskStatus(data.status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown status")

    going_done = new_status == TaskStatus.DONE and task.status != TaskStatus.DONE
    leaving_done = task.status == TaskStatus.DONE and new_status != TaskStatus.DONE
    if going_done and not can_complete(task, member_role, user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot complete this task")

    audit_before = snapshot_fields(task, TASK_AUDIT_FIELDS)
    await _apply_order(db, data.order)
    event_id = None
    if going_done:
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now(timezone.utc)
        task.completed_by = user.id
        event_id = (await _emit_completed_event(db, task, user)).id
    elif leaving_done:
        task.status = new_status
        task.completed_at = None
        task.completed_by = None
    else:
        task.status = new_status

    _record_status_audit(db, task, user, audit_before, "task.moved")
    queue_task_live_event(db, "task.moved", task)
    await db.commit()
    await publish_queued_events(db)
    if event_id:
        await dispatch_event(event_id)
    await db.refresh(task)
    return task


async def _member_role_for_task(db: AsyncSession, task: Task, user: User):
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
        return None
    return (await assert_member(db, task.workspace_id, user)).role


async def _apply_order(db: AsyncSession, order: list[str]) -> None:
    for idx, task_id in enumerate(order or []):
        task = await db.get(Task, task_id)
        if task is not None:
            task.position = idx


async def _emit_completed_event(db: AsyncSession, task: Task, user: User):
    is_personal = task.scope == TaskScope.PERSONAL
    return await emit_event(
        db,
        event_type=DomainEventType.TASK_COMPLETED,
        actor_id=user.id,
        entity_type="task",
        entity_id=task.id,
        workspace_id=task.workspace_id,
        privacy_level=PrivacyLevel.PRIVATE if is_personal else PrivacyLevel.WORKSPACE,
        payload={
            "scope": task.scope.value,
            "before_due": task.due_date is not None and date.today() <= task.due_date,
            "beneficiary_id": task.assignee_id or user.id,
            "activity_text": None if is_personal else f"закрыл задачу «{task.title}»",
        },
    )


def _record_status_audit(db: AsyncSession, task: Task, user: User, audit_before: dict, action: str) -> None:
    audit_after = snapshot_fields(task, TASK_AUDIT_FIELDS)
    before, after = diff_snapshots(audit_before, audit_after)
    if before:
        record_audit(
            db,
            workspace_id=task.workspace_id,
            actor_id=user.id,
            action=action,
            entity_type="task",
            entity_id=task.id,
            before=before,
            after=after,
            target_user_id=task.assignee_id,
            details={"changed_fields": list(after.keys())},
        )
