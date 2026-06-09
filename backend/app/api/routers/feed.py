from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.enums import NotificationType
from app.models import ActivityEvent, Notification, Pet, User, WallPresence, WorkspaceMember
from app.schemas import ActivityOut, NotificationOut, PetOut

router = APIRouter(tags=["activity"])
WALL_PRESENCE_TTL = timedelta(seconds=75)


@router.get("/workspaces/{workspace_id}/activity", response_model=list[ActivityOut])
async def activity_feed(
    workspace_id: str,
    limit: int = 30,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # FR-ACT-2: only this workspace; personal tasks never reach here (FR-ACT-3).
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(ActivityEvent)
        .where(ActivityEvent.workspace_id == workspace_id)
        .order_by(ActivityEvent.created_at.desc())
        .limit(min(limit, 100))
    )
    return rows.all()


@router.get("/workspaces/{workspace_id}/team-room")
async def team_room(
    workspace_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await require_membership(workspace_id, db, user)
    cutoff = datetime.now(timezone.utc) - WALL_PRESENCE_TTL
    await db.execute(
        delete(WallPresence)
        .where(WallPresence.workspace_id == workspace_id, WallPresence.last_seen_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    online_ids = (
        await db.scalars(
            select(WallPresence.user_id).where(WallPresence.workspace_id == workspace_id)
        )
    ).all()
    if online_ids:
        member_ids = (
            await db.scalars(
                select(WorkspaceMember.user_id).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id.in_(online_ids),
                )
            )
        ).all()
        pets = (await db.scalars(select(Pet).where(Pet.user_id.in_(member_ids)))).all()
    else:
        member_ids = []
        pets = []
    activity = (
        await db.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.workspace_id == workspace_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(20)
        )
    ).all()
    # Team Room exposes pets + public activity only — no personal task data (FR §16.7).
    pets_out = []
    for pet in pets:
        data = PetOut.model_validate(pet).model_dump()
        data["user_id"] = pet.user_id
        pets_out.append(data)
    return {
        "pets": pets_out,
        "online_count": len(member_ids),
        "activity": [ActivityOut.model_validate(a).model_dump() for a in activity],
    }


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = await db.scalars(
        select(Notification)
        .where(Notification.user_id == user.id)  # FR-NOTIF-4
        .where(Notification.type != NotificationType.WALL_POST)
        .order_by(Notification.created_at.desc())
    )
    return rows.all()


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    notif = await db.get(Notification, notification_id)
    if notif is None or notif.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    notif.is_read = True
    await db.commit()
    await db.refresh(notif)
    return notif


@router.patch("/notifications/read-all", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_read(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    rows = await db.scalars(
        select(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    for notif in rows.all():
        notif.is_read = True
    await db.commit()
    return None
