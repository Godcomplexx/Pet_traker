"""Стена рабочего пространства — лёгкая лента для участников."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.enums import NotificationType
from app.models import User, WallPost, WallReaction, WorkspaceMember
from app.schemas import WallPostCreate, WallPostOut, WallReactionIn
from app.services.notifications import create_notification

router = APIRouter(tags=["wall"])
WALL_TTL = timedelta(hours=24)


async def _cleanup_wall(db: AsyncSession, workspace_id: str) -> None:
    cutoff = datetime.now(timezone.utc) - WALL_TTL
    await db.execute(
        delete(WallPost)
        .where(WallPost.workspace_id == workspace_id, WallPost.created_at < cutoff)
        .execution_options(synchronize_session=False)
    )


async def _reaction_maps(
    db: AsyncSession, post_ids: list[str], user_id: str
) -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    if not post_ids:
        return {}, {}
    count_rows = (
        await db.execute(
            select(WallReaction.post_id, WallReaction.emoji, func.count(WallReaction.id))
            .where(WallReaction.post_id.in_(post_ids))
            .group_by(WallReaction.post_id, WallReaction.emoji)
        )
    ).all()
    counts: dict[str, dict[str, int]] = {}
    for post_id, emoji, count in count_rows:
        counts.setdefault(post_id, {})[emoji] = int(count)

    mine_rows = (
        await db.execute(
            select(WallReaction.post_id, WallReaction.emoji).where(
                WallReaction.post_id.in_(post_ids),
                WallReaction.user_id == user_id,
            )
        )
    ).all()
    mine: dict[str, list[str]] = {}
    for post_id, emoji in mine_rows:
        mine.setdefault(post_id, []).append(emoji)
    return counts, mine


def _wall_out(
    post: WallPost,
    author_name: str,
    counts: dict[str, dict[str, int]] | None = None,
    mine: dict[str, list[str]] | None = None,
) -> WallPostOut:
    return WallPostOut(
        id=post.id,
        author_id=post.author_id,
        author_name=author_name,
        text=post.text,
        image_data=post.image_data,
        reactions=(counts or {}).get(post.id, {}),
        my_reactions=(mine or {}).get(post.id, []),
        created_at=post.created_at,
    )


@router.get("/workspaces/{workspace_id}/wall", response_model=list[WallPostOut])
async def list_wall(
    workspace_id: str,
    limit: int = Query(50, le=100),
    before: str | None = None,  # id поста для пагинации «загрузить ещё»
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    await _cleanup_wall(db, workspace_id)
    await db.commit()
    q = select(WallPost, User.display_name, User.email).join(
        User, User.id == WallPost.author_id
    ).where(WallPost.workspace_id == workspace_id)
    if before:
        anchor = await db.get(WallPost, before)
        if anchor is not None:
            q = q.where(WallPost.created_at < anchor.created_at)
    q = q.order_by(WallPost.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).all()
    post_ids = [p.id for (p, _name, _email) in rows]
    counts, mine = await _reaction_maps(db, post_ids, user.id)
    return [
        _wall_out(p, (name or email or p.author_id[:8]), counts, mine)
        for (p, name, email) in rows
    ]


@router.post("/workspaces/{workspace_id}/wall", response_model=WallPostOut, status_code=status.HTTP_201_CREATED)
async def create_wall_post(
    workspace_id: str,
    data: WallPostCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    await _cleanup_wall(db, workspace_id)
    text = data.text.strip()
    if not text and not data.image_data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Добавьте текст или картинку")
    post = WallPost(workspace_id=workspace_id, author_id=user.id, text=text, image_data=data.image_data)
    db.add(post)
    await db.flush()
    member_ids = (
        await db.scalars(
            select(WorkspaceMember.user_id).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id != user.id,
            )
        )
    ).all()
    preview_src = text or "прикрепил(а) картинку"
    preview = preview_src if len(preview_src) <= 160 else preview_src[:157] + "..."
    for member_id in member_ids:
        await create_notification(
            db,
            user_id=member_id,
            type_=NotificationType.WALL_POST,
            title=f"{user.display_name or user.email or 'Участник'} написал(а) на стене",
            body=preview,
            workspace_id=workspace_id,
            entity_type="wall_post",
            entity_id=post.id,
        )
    await db.commit()
    await db.refresh(post)
    return _wall_out(post, (user.display_name or user.email or user.id[:8]))


@router.post("/wall/{post_id}/react", response_model=WallPostOut)
async def react_wall_post(
    post_id: str,
    data: WallReactionIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(WallPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пост не найден")
    await require_membership(post.workspace_id, db, user)
    await _cleanup_wall(db, post.workspace_id)
    existing = await db.scalar(
        select(WallReaction).where(
            WallReaction.post_id == post_id,
            WallReaction.user_id == user.id,
            WallReaction.emoji == data.emoji,
        )
    )
    if existing:
        await db.delete(existing)
    else:
        db.add(WallReaction(post_id=post_id, user_id=user.id, emoji=data.emoji))
    await db.commit()
    await db.refresh(post)
    author = await db.get(User, post.author_id)
    counts, mine = await _reaction_maps(db, [post.id], user.id)
    return _wall_out(post, ((author and (author.display_name or author.email)) or post.author_id[:8]), counts, mine)


@router.delete("/wall/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wall_post(
    post_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    post = await db.get(WallPost, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пост не найден")
    # удалять может только автор
    if post.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Можно удалять только свои сообщения")
    await db.delete(post)
    await db.commit()
