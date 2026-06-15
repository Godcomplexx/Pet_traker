"""Notification creation helpers (spec §8.10). Personal context never notifies others."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import NotificationType
from app.models import Notification, User, WorkspaceMember
from app.services.realtime import make_event, queue_live_event


@dataclass(frozen=True)
class MentionNotificationInput:
    workspace_id: str
    actor_id: str
    mentioned_user_ids: list[str]
    mentioned_emails: list[str]
    entity_type: str
    entity_id: str
    body: str | None = None


@dataclass(frozen=True)
class TaskCommentNotificationInput:
    workspace_id: str
    actor_id: str
    task_id: str
    title: str
    body: str | None
    recipient_ids: list[str]


async def create_notification(
    db: AsyncSession,
    *,
    user_id: str,
    type_: NotificationType,
    title: str,
    body: str | None = None,
    workspace_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        workspace_id=workspace_id,
        type=type_,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    db.add(notif)
    queue_live_event(
        db,
        make_event(
            "notification.created",
            {
                "type": type_.value,
                "title": title,
                "body": body,
                "entity_type": entity_type,
                "entity_id": entity_id,
            },
            workspace_id=workspace_id,
            target_user_ids=[user_id],
        ),
    )
    return notif


async def notify_assignment(
    db: AsyncSession, *, assignee_id: str, actor_id: str, workspace_id: str, task_id: str, title: str
) -> None:
    # FR-NOTIF-1. Don't notify self-assignment.
    if assignee_id == actor_id:
        return
    await create_notification(
        db,
        user_id=assignee_id,
        type_=NotificationType.TASK_ASSIGNED,
        title="Вам назначена задача",
        body=title,
        workspace_id=workspace_id,
        entity_type="task",
        entity_id=task_id,
    )


async def notify_mentions(
    db: AsyncSession,
    options: MentionNotificationInput | None = None,
    **notification_kwargs,
) -> int:
    """Create MENTION notifications for valid workspace members. Returns count created.

    Only workspace members are notified (FR-COM-6); unknown users/emails are ignored
    (EC-5); the author is never notified about their own mention.
    """
    data = options or MentionNotificationInput(**notification_kwargs)
    # Resolve emails → user ids.
    resolved: set[str] = set(data.mentioned_user_ids)
    if data.mentioned_emails:
        rows = await db.scalars(select(User).where(User.email.in_(data.mentioned_emails)))
        resolved.update(u.id for u in rows.all())
    resolved.discard(data.actor_id)
    if not resolved:
        return 0

    member_ids = set(
        (
            await db.scalars(
                select(WorkspaceMember.user_id).where(
                    WorkspaceMember.workspace_id == data.workspace_id,
                    WorkspaceMember.user_id.in_(resolved),
                )
            )
        ).all()
    )

    for uid in member_ids:
        await create_notification(
            db,
            user_id=uid,
            type_=NotificationType.MENTION,
            title="Вас упомянули в комментарии",
            body=data.body,
            workspace_id=data.workspace_id,
            entity_type=data.entity_type,
            entity_id=data.entity_id,
        )
    return len(member_ids)


async def notify_task_comment(
    db: AsyncSession,
    options: TaskCommentNotificationInput | None = None,
    **notification_kwargs,
) -> int:
    data = options or TaskCommentNotificationInput(**notification_kwargs)
    recipients = set(data.recipient_ids)
    recipients.discard(data.actor_id)
    if not recipients:
        return 0

    member_ids = set(
        (
            await db.scalars(
                select(WorkspaceMember.user_id).where(
                    WorkspaceMember.workspace_id == data.workspace_id,
                    WorkspaceMember.user_id.in_(recipients),
                )
            )
        ).all()
    )
    for uid in member_ids:
        await create_notification(
            db,
            user_id=uid,
            type_=NotificationType.MENTION,
            title=data.title,
            body=data.body,
            workspace_id=data.workspace_id,
            entity_type="task",
            entity_id=data.task_id,
        )
    return len(member_ids)
