from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ELEVATED_ROLES,
    WRITE_ROLES,
    get_current_user,
    require_membership,
)
from app.core.database import get_db
from app.enums import (
    DomainEventType,
    PrivacyLevel,
    ProjectStatus,
)
from app.models import Article, Project, ProjectMember, Task, User, WorkspaceMember
from app.schemas import (
    ArticleOut,
    ProjectCreate,
    ProjectMemberAdd,
    ProjectMemberOut,
    ProjectOut,
    ProjectStatusUpdate,
    ProjectUpdate,
    TaskOut,
)
from app.services.dispatch import dispatch_event
from app.services.events import emit_event

router = APIRouter(tags=["projects"])


async def _get_project_for_member(db: AsyncSession, project_id: str, user: User) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await require_membership(project.workspace_id, db, user)  # FR-PROJ-7
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
    if member.role not in WRITE_ROLES:  # FR-WS-5: VIEWER cannot create
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    project = Project(
        workspace_id=workspace_id,
        name=data.name,
        description=data.description,
        type=data.type,
        deadline=data.deadline,
        owner_id=user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/workspaces/{workspace_id}/projects", response_model=list[ProjectOut])
async def list_projects(
    workspace_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(Project).where(Project.workspace_id == workspace_id).order_by(Project.created_at.desc())
    )
    return rows.all()


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
    project = await _get_project_for_member(db, project_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
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

    project.status = data.status
    # FR-PROJ-6 + FR-GAME-6: reward project completion.
    event = await emit_event(
        db,
        event_type=DomainEventType.PROJECT_STATUS_CHANGED,
        actor_id=user.id,
        entity_type="project",
        entity_id=project.id,
        workspace_id=project.workspace_id,
        privacy_level=PrivacyLevel.WORKSPACE,
        payload={
            "status": data.status.value,
            "activity_text": f"перевёл проект «{project.name}» в {data.status.value}",
        },
    )
    event_id = event.id
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
    rows = await db.scalars(select(Task).where(Task.project_id == project_id))
    return rows.all()


@router.get("/projects/{project_id}/articles", response_model=list[ArticleOut])
async def project_articles(
    project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_project_for_member(db, project_id, user)
    rows = await db.scalars(select(Article).where(Article.project_id == project_id))
    return rows.all()


# ── участники проекта (ТЗ §5.3, §12.4) ──
@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
async def project_members(
    project_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await _get_project_for_member(db, project_id, user)
    rows = await db.execute(
        select(ProjectMember, User.display_name, User.email)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
    )
    return [
        ProjectMemberOut(id=m.id, user_id=m.user_id, role=m.role, display_name=dn, email=em)
        for m, dn, em in rows.all()
    ]


@router.post("/projects/{project_id}/members", response_model=ProjectMemberOut, status_code=201)
async def add_project_member(
    project_id: str,
    data: ProjectMemberAdd,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    member = await require_membership(project.workspace_id, db, user)
    if member.role not in ELEVATED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    # Участник проекта должен входить в workspace.
    in_ws = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == project.workspace_id,
            WorkspaceMember.user_id == data.user_id,
        )
    )
    if in_ws is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not a workspace member")
    exists = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == data.user_id
        )
    )
    if exists:
        exists.role = data.role  # обновляем роль, если уже участник
        await db.commit()
        await db.refresh(exists)
        target = exists
    else:
        target = ProjectMember(project_id=project_id, user_id=data.user_id, role=data.role)
        db.add(target)
        await db.commit()
        await db.refresh(target)
    u = await db.get(User, target.user_id)
    return ProjectMemberOut(
        id=target.id, user_id=target.user_id, role=target.role,
        display_name=u.display_name if u else None, email=u.email if u else None,
    )


@router.delete("/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    member = await require_membership(project.workspace_id, db, user)
    if member.role not in ELEVATED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    target = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    await db.delete(target)
    await db.commit()
    return None
