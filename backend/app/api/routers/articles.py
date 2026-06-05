from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ELEVATED_ROLES, WRITE_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.enums import ArticleStatus, DomainEventType, PrivacyLevel, TaskStatus
from app.models import Article, ArticleMember, Project, Task, User, WorkspaceMember
from app.schemas import (
    ArticleCreate,
    ArticleMemberAdd,
    ArticleMemberOut,
    ArticleOut,
    ArticleStatusUpdate,
    BoardMove,
    TaskOut,
)
from app.services.dispatch import dispatch_event
from app.services.events import emit_event

router = APIRouter(tags=["articles"])

REWARDED_STATUSES = {ArticleStatus.SUBMITTED, ArticleStatus.ACCEPTED, ArticleStatus.PUBLISHED}


async def _enrich_articles(db: AsyncSession, articles: list[Article]) -> list[ArticleOut]:
    """Дополнить статьи счётчиками задач и участниками для карточек доски."""
    if not articles:
        return []
    ids = [a.id for a in articles]
    task_rows = (
        await db.execute(
            select(
                Task.article_id,
                func.count(Task.id),
                func.count(Task.id).filter(Task.status == TaskStatus.DONE),
            )
            .where(Task.article_id.in_(ids))
            .group_by(Task.article_id)
        )
    ).all()
    task_map = {aid: (total, done) for aid, total, done in task_rows}

    mem_rows = (
        await db.execute(
            select(ArticleMember.article_id, ArticleMember.user_id).where(
                ArticleMember.article_id.in_(ids)
            )
        )
    ).all()
    mem_map: dict[str, list[str]] = {}
    for aid, uid in mem_rows:
        mem_map.setdefault(aid, []).append(uid)

    out = []
    for a in articles:
        total, done = task_map.get(a.id, (0, 0))
        o = ArticleOut.model_validate(a)
        o.task_total = total
        o.task_done = done
        o.member_ids = mem_map.get(a.id, [])
        out.append(o)
    return out


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
    workspace_id: str,
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    stmt = select(Article).where(Article.workspace_id == workspace_id)
    if q:
        stmt = stmt.where(Article.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(Article.position.asc(), Article.created_at.desc())
    rows = (await db.scalars(stmt)).all()
    return await _enrich_articles(db, list(rows))


@router.patch("/articles/{article_id}/move", response_model=ArticleOut)
async def move_article(
    article_id: str,
    data: BoardMove,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """DnD на доске статей: сменить publication-статус (колонку) и/или порядок."""
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    member = await require_membership(article.workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")

    try:
        new_status = ArticleStatus(data.status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown status")

    status_changed = article.status != new_status
    article.status = new_status

    if data.order:
        for idx, aid in enumerate(data.order):
            a = await db.get(Article, aid)
            if a and a.workspace_id == article.workspace_id:
                a.position = idx

    event_id = None
    if status_changed:
        event = await emit_event(
            db,
            event_type=DomainEventType.ARTICLE_STATUS_CHANGED,
            actor_id=user.id,
            entity_type="article",
            entity_id=article.id,
            workspace_id=article.workspace_id,
            privacy_level=PrivacyLevel.WORKSPACE,
            payload={
                "status": new_status.value,
                "beneficiary_id": article.owner_id,
                "activity_text": f"перевёл статью «{article.title}» в {new_status.value}",
            },
        )
        event_id = event.id

    await db.commit()
    if event_id and new_status in REWARDED_STATUSES:
        await dispatch_event(event_id)
    await db.refresh(article)
    return article


@router.get("/articles/{article_id}", response_model=ArticleOut)
async def get_article(
    article_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await require_membership(article.workspace_id, db, user)  # FR-ART-5
    return article


@router.get("/articles/{article_id}/tasks", response_model=list[TaskOut])
async def article_tasks(
    article_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await require_membership(article.workspace_id, db, user)
    rows = await db.scalars(
        select(Task).where(Task.article_id == article_id).order_by(
            Task.position.asc(), Task.created_at.asc()
        )
    )
    return rows.all()


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


# ── участники статьи (ТЗ §5.4, §12.4) ──
@router.get("/articles/{article_id}/members", response_model=list[ArticleMemberOut])
async def article_members(
    article_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await require_membership(article.workspace_id, db, user)
    rows = await db.execute(
        select(ArticleMember, User.display_name, User.email)
        .join(User, User.id == ArticleMember.user_id)
        .where(ArticleMember.article_id == article_id)
    )
    return [
        ArticleMemberOut(id=m.id, user_id=m.user_id, role=m.role, display_name=dn, email=em)
        for m, dn, em in rows.all()
    ]


@router.post("/articles/{article_id}/members", response_model=ArticleMemberOut, status_code=201)
async def add_article_member(
    article_id: str,
    data: ArticleMemberAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    member = await require_membership(article.workspace_id, db, user)
    if member.role not in ELEVATED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    in_ws = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == article.workspace_id,
            WorkspaceMember.user_id == data.user_id,
        )
    )
    if in_ws is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not a workspace member")
    exists = await db.scalar(
        select(ArticleMember).where(
            ArticleMember.article_id == article_id,
            ArticleMember.user_id == data.user_id,
        )
    )
    if exists:
        exists.role = data.role
        await db.commit()
        await db.refresh(exists)
        target = exists
    else:
        target = ArticleMember(article_id=article_id, user_id=data.user_id, role=data.role)
        db.add(target)
        await db.commit()
        await db.refresh(target)
    u = await db.get(User, target.user_id)
    return ArticleMemberOut(
        id=target.id,
        user_id=target.user_id,
        role=target.role,
        display_name=u.display_name if u else None,
        email=u.email if u else None,
    )


@router.delete("/articles/{article_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_article_member(
    article_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    member = await require_membership(article.workspace_id, db, user)
    if member.role not in ELEVATED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    target = await db.scalar(
        select(ArticleMember).where(
            ArticleMember.article_id == article_id,
            ArticleMember.user_id == user_id,
        )
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    await db.delete(target)
    await db.commit()
    return None
