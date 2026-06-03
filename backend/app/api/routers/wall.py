"""Стена рабочего пространства — лёгкая текстовая лента для участников."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.models import User, WallPost
from app.schemas import WallPostCreate, WallPostOut

router = APIRouter(tags=["wall"])


@router.get("/workspaces/{workspace_id}/wall", response_model=list[WallPostOut])
async def list_wall(
    workspace_id: str,
    limit: int = Query(50, le=100),
    before: str | None = None,  # id поста для пагинации «загрузить ещё»
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    q = select(WallPost, User.display_name, User.email).join(
        User, User.id == WallPost.author_id
    ).where(WallPost.workspace_id == workspace_id)
    if before:
        anchor = await db.get(WallPost, before)
        if anchor is not None:
            q = q.where(WallPost.created_at < anchor.created_at)
    q = q.order_by(WallPost.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).all()
    return [
        WallPostOut(
            id=p.id,
            author_id=p.author_id,
            author_name=(name or email or p.author_id[:8]),
            text=p.text,
            created_at=p.created_at,
        )
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
    text = data.text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Пустое сообщение")
    post = WallPost(workspace_id=workspace_id, author_id=user.id, text=text)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return WallPostOut(
        id=post.id,
        author_id=user.id,
        author_name=(user.display_name or user.email or user.id[:8]),
        text=post.text,
        created_at=post.created_at,
    )


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
