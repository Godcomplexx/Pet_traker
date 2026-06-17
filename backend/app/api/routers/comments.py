from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WRITE_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.enums import DomainEventType, PrivacyLevel, TaskScope, TaskVisibility
from app.models import Article, Comment, Project, Task, User
from app.schemas import CommentCreate, CommentOut, CommentUpdate
from app.services.dispatch import dispatch_event
from app.services.events import emit_event
from app.services.mentions import extract_mentioned_emails
from app.services.notifications import notify_mentions, notify_task_comment
from app.services.realtime import make_event, publish_queued_events, queue_live_event

router = APIRouter(tags=["comments"])


async def _team_guard(db: AsyncSession, workspace_id: str, user: User) -> None:
    member = await require_membership(workspace_id, db, user)
    if member.role not in WRITE_ROLES:  # FR-WS-5
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")


async def _add_team_comment(
    db: AsyncSession,
    *,
    user: User,
    text: str,
    mention_user_ids: list[str],
    workspace_id: str,
    entity_type: str,
    project_id: str | None = None,
    article_id: str | None = None,
    task_id: str | None = None,
) -> Comment:
    comment = Comment(
        workspace_id=workspace_id,
        project_id=project_id,
        article_id=article_id,
        task_id=task_id,
        author_id=user.id,
        text=text,
        visibility=TaskVisibility.WORKSPACE,
    )
    db.add(comment)
    await db.flush()

    target_id = task_id or project_id or article_id or comment.id
    comment_preview = text[:180]
    await notify_mentions(
        db,
        workspace_id=workspace_id,
        actor_id=user.id,
        mentioned_user_ids=mention_user_ids,
        mentioned_emails=extract_mentioned_emails(text),
        entity_type=entity_type,
        entity_id=target_id,
        body=comment_preview,
    )
    if task_id:
        task = await db.get(Task, task_id)
        if task is not None:
            recipients = {
                task.owner_id,
                task.created_by,
                task.assignee_id,
                *(task.assignees or []),
            }
            recipients.discard(None)
            recipients.difference_update(mention_user_ids)
            await notify_task_comment(
                db,
                workspace_id=workspace_id,
                actor_id=user.id,
                task_id=task_id,
                title=f"Новый комментарий к задаче: {task.title}",
                body=comment_preview,
                recipient_ids=list(recipients),
            )

    # FR-GAME (comment XP, daily-capped in the worker).
    event = await emit_event(
        db,
        event_type=DomainEventType.COMMENT_ADDED,
        actor_id=user.id,
        entity_type=entity_type,
        entity_id=comment.id,
        workspace_id=workspace_id,
        privacy_level=PrivacyLevel.WORKSPACE,
        payload={"activity_text": None},  # comments aren't surfaced in activity feed
    )
    event_id = event.id
    queue_live_event(
        db,
        make_event(
            "comment.created",
            {
                "comment_id": comment.id,
                "entity_type": entity_type,
                "entity_id": target_id,
                "text": comment.text,
                "author_id": user.id,
                "author_name": user.display_name,
                "created_at": comment.created_at.isoformat(),
            },
            workspace_id=workspace_id,
        ),
    )
    await db.commit()
    await publish_queued_events(db)
    await dispatch_event(event_id)
    await db.refresh(comment)
    return comment


# ── projects ──
@router.post("/projects/{project_id}/comments", response_model=CommentOut, status_code=201)
async def comment_project(
    project_id: str,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await _team_guard(db, project.workspace_id, user)
    return await _add_team_comment(
        db, user=user, text=data.text, mention_user_ids=data.mention_user_ids,
        workspace_id=project.workspace_id, entity_type="project", project_id=project_id,
    )


@router.get("/projects/{project_id}/comments", response_model=list[CommentOut])
async def list_project_comments(
    project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await require_membership(project.workspace_id, db, user)
    rows = await db.scalars(
        select(Comment).where(Comment.project_id == project_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at)
    )
    return rows.all()


# ── articles ──
@router.post("/articles/{article_id}/comments", response_model=CommentOut, status_code=201)
async def comment_article(
    article_id: str,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await _team_guard(db, article.workspace_id, user)
    return await _add_team_comment(
        db, user=user, text=data.text, mention_user_ids=data.mention_user_ids,
        workspace_id=article.workspace_id, entity_type="article", article_id=article_id,
    )


@router.get("/articles/{article_id}/comments", response_model=list[CommentOut])
async def list_article_comments(
    article_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await require_membership(article.workspace_id, db, user)
    rows = await db.scalars(
        select(Comment).where(Comment.article_id == article_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at)
    )
    return rows.all()


# ── tasks (team or personal) ──
@router.post("/tasks/{task_id}/comments", response_model=CommentOut, status_code=201)
async def comment_task(
    task_id: str,
    data: CommentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    if task.scope == TaskScope.PERSONAL:
        # FR-COM-4 + FR-PT-9: owner-only, and mentions never notify anyone else.
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
        comment = Comment(
            task_id=task_id,
            author_id=user.id,
            text=data.text,
            visibility=TaskVisibility.PRIVATE,
        )
        db.add(comment)
        await db.flush()
        queue_live_event(
            db,
            make_event(
                "comment.created",
                {
                    "comment_id": comment.id,
                    "entity_type": "task",
                    "entity_id": task_id,
                    "text": comment.text,
                    "author_id": user.id,
                    "author_name": user.display_name,
                    "created_at": comment.created_at.isoformat(),
                },
                target_user_ids=[task.owner_id],
            ),
        )
        await db.commit()
        await publish_queued_events(db)
        await db.refresh(comment)
        return comment

    await _team_guard(db, task.workspace_id, user)
    return await _add_team_comment(
        db, user=user, text=data.text, mention_user_ids=data.mention_user_ids,
        workspace_id=task.workspace_id, entity_type="task", task_id=task_id,
    )


@router.get("/tasks/{task_id}/comments", response_model=list[CommentOut])
async def list_task_comments(
    task_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    else:
        await require_membership(task.workspace_id, db, user)
    rows = await db.scalars(
        select(Comment).where(Comment.task_id == task_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at)
    )
    return rows.all()


# ── edit / delete (author only — FR-COM-7) ──
@router.patch("/comments/{comment_id}", response_model=CommentOut)
async def edit_comment(
    comment_id: str,
    data: CommentUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.deleted_at is not None or comment.author_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    comment.text = data.text
    target_id = comment.task_id or comment.project_id or comment.article_id or comment.id
    queue_live_event(
        db,
        make_event(
            "comment.updated",
            {
                "comment_id": comment.id,
                "entity_type": "task" if comment.task_id else "project" if comment.project_id else "article",
                "entity_id": target_id,
                "text": comment.text,
            },
            workspace_id=comment.workspace_id,
            target_user_ids=[comment.author_id] if comment.workspace_id is None else [],
        ),
    )
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(comment)
    return comment


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    comment = await db.get(Comment, comment_id)
    if comment is None or comment.deleted_at is not None or comment.author_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comment not found")
    from datetime import datetime, timezone

    comment.deleted_at = datetime.now(timezone.utc)
    target_id = comment.task_id or comment.project_id or comment.article_id or comment.id
    queue_live_event(
        db,
        make_event(
            "comment.deleted",
            {
                "comment_id": comment.id,
                "entity_type": "task" if comment.task_id else "project" if comment.project_id else "article",
                "entity_id": target_id,
            },
            workspace_id=comment.workspace_id,
            target_user_ids=[comment.author_id] if comment.workspace_id is None else [],
        ),
    )
    await db.commit()
    await publish_queued_events(db)
    return None
