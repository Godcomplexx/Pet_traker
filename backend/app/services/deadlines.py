"""Deadline reminders (FR-NOTIF-3). Idempotent: one DEADLINE notice per task/user."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationType, TaskScope, TaskStatus
from app.models import Notification, Task
from app.services.notifications import create_notification

CLOSED = {TaskStatus.DONE, TaskStatus.CANCELLED}


async def run_deadline_check(db: AsyncSession, *, horizon_days: int = 1) -> int:
    """Notify owners/assignees of tasks due within `horizon_days`. Returns notices created."""
    until = date.today() + timedelta(days=horizon_days)
    rows = await db.scalars(
        select(Task).where(
            Task.due_date.is_not(None),
            Task.due_date <= until,
            Task.status.notin_(CLOSED),
        )
    )

    created = 0
    for task in rows.all():
        recipient = task.assignee_id if task.scope != TaskScope.PERSONAL else task.owner_id
        if not recipient:
            continue
        # Skip if we've already reminded this user about this task.
        exists = await db.scalar(
            select(Notification).where(
                Notification.user_id == recipient,
                Notification.type == NotificationType.DEADLINE,
                Notification.entity_id == task.id,
            )
        )
        if exists:
            continue
        await create_notification(
            db,
            user_id=recipient,
            type_=NotificationType.DEADLINE,
            title="Приближается дедлайн",
            body=task.title,
            workspace_id=task.workspace_id,
            entity_type="task",
            entity_id=task.id,
        )
        created += 1

    await db.commit()
    return created
