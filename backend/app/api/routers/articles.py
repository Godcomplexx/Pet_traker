from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ELEVATED_ROLES, WRITE_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.enums import ArticleStatus, DomainEventType, PrivacyLevel
from app.models import Article, ArticleMember, Project, User, WorkspaceMember
from app.schemas import (
    ArticleCreate,
    ArticleMemberAdd,
    ArticleMemberOut,
    ArticleOut,
    ArticleStatusUpdate,
)
from app.services.dispatch import dispatch_event
from app.services.events import emit_event

router = APIRouter(tags=["articles"])

REWARDED_STATUSES = {ArticleStatus.SUBMITTED, ArticleStatus.ACCEPTED, ArticleStatus.PUBLISHED}


async def _validate_project(db: AsyncSession, workspace_id: str, project_id: str | None) -> None:
    if project_id is None:
        return
    project = await db.get(Project, project_id)
    # EC-13: article workspace_id must match its project's workspace_id.
    if project is None or project.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Project not in this workspace")


@router.post(
    "/workspaces/{workspace_id}/articles",
    response_model=ArticleOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_article(
    workspace_id: str,
    data: ArticleCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    await _validate_project(db, workspace_id, data.project_id)

    article = Article(
        workspace_id=workspace_id,
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        target_journal=data.target_journal,
        document_url=data.document_url,
        deadline=data.deadline,
        owner_id=user.id,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


@router.get("/workspaces/{workspace_id}/articles", response_model=list[ArticleOut])
async def list_articles(
    workspace_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(Article).where(Article.workspace_id == workspace_id).order_by(Article.created_at.desc())
    )
    return rows.all()


@router.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await require_membership(article.workspace_id, db, user)  # FR-ART-5
    return article


@router.patch("/articles/{article_id}/status", response_model=ArticleOut)
async def change_article_status(
    article_id: str,
    data: ArticleStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    member = await require_membership(article.workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")

    article.status = data.status
    # FR-ART-4 + FR-GAME-5
    event = await emit_event(
        db,
        event_type=DomainEventType.ARTICLE_STATUS_CHANGED,
        actor_id=user.id,
        entity_type="article",
        entity_id=article.id,
        workspace_id=article.workspace_id,
        privacy_level=PrivacyLevel.WORKSPACE,
        payload={
            "status": data.status.value,
            "beneficiary_id": article.owner_id,
            "activity_text": f"перевёл статью «{article.title}» в {data.status.value}",
        },
    )
    event_id = event.id
    await db.commit()
    if data.status in REWARDED_STATUSES:
        await dispatch_event(event_id)
    await db.refresh(article)
    return article
