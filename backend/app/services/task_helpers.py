from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ELEVATED_ROLES, require_membership
from app.enums import TaskScope
from app.models import Task, User, WorkspaceMember
from app.services.realtime import make_event, queue_live_event

TASK_AUDIT_FIELDS = (
    "title",
    "description",
    "status",
    "priority",
    "type",
    "assignee_id",
    "assignees",
    "due_date",
    "completed_by",
    "completed_at",
)


async def assert_member(db: AsyncSession, workspace_id: str, user: User) -> WorkspaceMember:
    return await require_membership(workspace_id, db, user)


async def load_task_with_access(db: AsyncSession, task_id: str, user: User) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    else:
        await assert_member(db, task.workspace_id, user)
    return task


def queue_task_live_event(db: AsyncSession, type_: str, task: Task) -> None:
    payload = {"task_id": task.id, "status": task.status.value if task.status else None}
    if task.scope == TaskScope.PERSONAL:
        queue_live_event(db, make_event(type_, payload, target_user_ids=[task.owner_id]))
    else:
        queue_live_event(db, make_event(type_, payload, workspace_id=task.workspace_id))


async def validate_workspace_assignees(
    db: AsyncSession, workspace_id: str, assignee_ids: list[str]
) -> list[str]:
    ids = list(dict.fromkeys(assignee_ids))
    if not ids:
        return []
    member_ids = set(
        (
            await db.scalars(
                select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
            )
        ).all()
    )
    bad = [assignee_id for assignee_id in ids if assignee_id not in member_ids]
    if bad:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Исполнитель не состоит в лаборатории")
    return ids


def can_complete(task: Task, member_role, user: User) -> bool:
    if task.scope == TaskScope.PERSONAL:
        return task.owner_id == user.id
    if task.assignee_id == user.id or task.created_by == user.id:
        return True
    return member_role in ELEVATED_ROLES
