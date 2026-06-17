from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ELEVATED_ROLES, WRITE_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.enums import DomainEventType, PrivacyLevel, ProjectStatus, TaskStatus
from app.models import Article, Project, ProjectMember, Task, User
from app.schemas import ArticleOut, BoardMove, ProjectCreate, ProjectOut, ProjectStatusUpdate, ProjectUpdate, TaskOut
from app.services.audit import diff_snapshots, record_audit, snapshot_fields
from app.services.dispatch import dispatch_event
from app.services.events import emit_event

router = APIRouter(tags=["projects"])

PROJECT_AUDIT_FIELDS = ("name", "description", "type", "status", "deadline", "owner_id")


async def _enrich_projects(db: AsyncSession, projects: list[Project]) -> list[ProjectOut]:
    if not projects:
        return []
    ids = [project.id for project in projects]
    task_rows = (
        await db.execute(
            select(
                Task.project_id,
                func.count(Task.id),
                func.count(Task.id).filter(Task.status == TaskStatus.DONE),
            )
            .where(Task.project_id.in_(ids))
            .group_by(Task.project_id)
        )
    ).all()
    article_rows = (
        await db.execute(
            select(Article.project_id, func.count(Article.id))
            .where(Article.project_id.in_(ids))
            .group_by(Article.project_id)
        )
    ).all()
    member_rows = (
        await db.execute(
            select(ProjectMember.project_id, ProjectMember.user_id).where(ProjectMember.project_id.in_(ids))
        )
    ).all()
    task_map = {project_id: (total, done) for project_id, total, done in task_rows}
    article_map = {project_id: count for project_id, count in article_rows}
    member_map: dict[str, list[str]] = {}
    for project_id, user_id in member_rows:
        member_map.setdefault(project_id, []).append(user_id)

    out = []
    for project in projects:
        total, done = task_map.get(project.id, (0, 0))
        item = ProjectOut.model_validate(project)
        item.task_total = total
        item.task_done = done
        item.article_count = article_map.get(project.id, 0)
        item.member_ids = member_map.get(project.id, [])
        out.append(item)
    return out


async def _get_project_for_member(db: AsyncSession, project_id: str, user: User) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await require_membership(project.workspace_id, db, user)
    return project


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    tags=["projects"],
)
async def create_project(
    workspace_id: str,
    data: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    project = Project(
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        type=data.type,
        deadline=data.deadline,
        owner_id=user.id,
        **({"status": data.status} if data.status else {}),
    )
    db.add(project)
    await db.flush()
    record_audit(
        db,
        workspace_id=workspace_id,
        actor_id=user.id,
        action="project.created",
        entity_type="project",
        entity_id=project.id,
        after=snapshot_fields(project, PROJECT_AUDIT_FIELDS),
    )
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/workspaces/{workspace_id}/projects", response_model=list[ProjectOut])
async def list_projects(
    workspace_id: str,
    q: str | None = None,
    type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    stmt = select(Project).where(Project.workspace_id == workspace_id)
    if q:
        stmt = stmt.where(Project.name.ilike(f"%{q}%"))
    if type:
        stmt = stmt.where(Project.type == type)
    rows = (await db.scalars(stmt.order_by(Project.position.asc(), Project.created_at.desc()))).all()
    return await _enrich_projects(db, list(rows))


@router.patch("/projects/{project_id}/move", response_model=ProjectOut)
async def move_project(
    project_id: str,
    data: BoardMove,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    member = await require_membership(project.workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    try:
        new_status = ProjectStatus(data.status)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown status")

    audit_before = snapshot_fields(project, PROJECT_AUDIT_FIELDS)
    status_changed = project.status != new_status
    project.status = new_status
    await _apply_project_order(db, project.workspace_id, data.order)
    event_id = None
    if status_changed:
        event_id = (await _emit_status_event(db, project, user.id, new_status)).id
    _record_project_audit(db, project, user.id, audit_before, "project.moved")
    await db.commit()
    if event_id and new_status == ProjectStatus.DONE:
        await dispatch_event(event_id)
    await db.refresh(project)
    return project


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    return await _get_project_for_member(db, project_id, user)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    member = await require_membership(project.workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    audit_before = snapshot_fields(project, PROJECT_AUDIT_FIELDS)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    _record_project_audit(db, project, user.id, audit_before, "project.updated")
    await db.commit()
    await db.refresh(project)
    return project


@router.patch("/projects/{project_id}/status", response_model=ProjectOut)
async def change_project_status(
    project_id: str,
    data: ProjectStatusUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    member = await require_membership(project.workspace_id, db, user)
    if member.role not in ELEVATED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    audit_before = snapshot_fields(project, PROJECT_AUDIT_FIELDS)
    project.status = data.status
    event_id = (await _emit_status_event(db, project, user.id, data.status)).id
    _record_project_audit(db, project, user.id, audit_before, "project.status_changed")
    await db.commit()
    if data.status == ProjectStatus.DONE:
        await dispatch_event(event_id)
    await db.refresh(project)
    return project


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
async def project_tasks(
    project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_project_for_member(db, project_id, user)
    rows = await db.scalars(
        select(Task).where(Task.project_id == project_id).order_by(Task.position.asc(), Task.created_at.asc())
    )
    return rows.all()


@router.get("/projects/{project_id}/articles", response_model=list[ArticleOut])
async def project_articles(
    project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_project_for_member(db, project_id, user)
    rows = await db.scalars(select(Article).where(Article.project_id == project_id))
    return rows.all()


async def _apply_project_order(db: AsyncSession, workspace_id: str, order: list[str]) -> None:
    for idx, project_id in enumerate(order or []):
        project = await db.get(Project, project_id)
        if project and project.workspace_id == workspace_id:
            project.position = idx


async def _emit_status_event(db: AsyncSession, project: Project, actor_id: str, status_: ProjectStatus):
    return await emit_event(
        db,
        event_type=DomainEventType.PROJECT_STATUS_CHANGED,
        actor_id=actor_id,
        entity_type="project",
        entity_id=project.id,
        workspace_id=project.workspace_id,
        privacy_level=PrivacyLevel.WORKSPACE,
        payload={"status": status_.value, "activity_text": f"перевёл проект «{project.name}» в {status_.value}"},
    )


def _record_project_audit(
    db: AsyncSession, project: Project, actor_id: str, audit_before: dict, action: str
) -> None:
    audit_after = snapshot_fields(project, PROJECT_AUDIT_FIELDS)
    before, after = diff_snapshots(audit_before, audit_after)
    if before:
        record_audit(
            db,
            workspace_id=project.workspace_id,
            actor_id=actor_id,
            action=action,
            entity_type="project",
            entity_id=project.id,
            before=before,
            after=after,
            details={"changed_fields": list(after.keys())},
        )
