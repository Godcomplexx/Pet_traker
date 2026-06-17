from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ELEVATED_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.models import Project, ProjectMember, User, WorkspaceMember
from app.schemas import ProjectMemberAdd, ProjectMemberOut
from app.services.audit import record_audit

router = APIRouter(tags=["projects"])


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
    project = await _get_project_for_admin(db, project_id, user)
    await _assert_workspace_member(db, project.workspace_id, data.user_id)
    target = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == data.user_id
        )
    )
    if target:
        before_role = target.role
        target.role = data.role
        _audit_member_change(
            db,
            {
                "project": project,
                "actor_id": user.id,
                "target_user_id": data.user_id,
                "action": "project.member_role_changed",
                "before_role": before_role,
                "after_role": data.role,
            },
        )
    else:
        target = ProjectMember(project_id=project_id, user_id=data.user_id, role=data.role)
        db.add(target)
        await db.flush()
        _audit_member_change(
            db,
            {
                "project": project,
                "actor_id": user.id,
                "target_user_id": data.user_id,
                "action": "project.member_added",
                "before_role": None,
                "after_role": data.role,
            },
        )
    await db.commit()
    await db.refresh(target)
    target_user = await db.get(User, target.user_id)
    return ProjectMemberOut(
        id=target.id,
        user_id=target.user_id,
        role=target.role,
        display_name=target_user.display_name if target_user else None,
        email=target_user.email if target_user else None,
    )


@router.delete("/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_project_member(
    project_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project_for_admin(db, project_id, user)
    target = await db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
        )
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    _audit_member_change(
        db,
        {
            "project": project,
            "actor_id": user.id,
            "target_user_id": user_id,
            "action": "project.member_removed",
            "before_role": target.role,
            "after_role": None,
        },
    )
    await db.delete(target)
    await db.commit()
    return None


async def _get_project_for_member(db: AsyncSession, project_id: str, user: User) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await require_membership(project.workspace_id, db, user)
    return project


async def _get_project_for_admin(db: AsyncSession, project_id: str, user: User) -> Project:
    project = await _get_project_for_member(db, project_id, user)
    member = await require_membership(project.workspace_id, db, user)
    if member.role not in ELEVATED_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    return project


async def _assert_workspace_member(db: AsyncSession, workspace_id: str, user_id: str) -> None:
    in_ws = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if in_ws is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "User is not a workspace member")


def _audit_member_change(db: AsyncSession, change: dict) -> None:
    project = change["project"]
    before_role = change.get("before_role")
    after_role = change.get("after_role")
    record_audit(
        db,
        workspace_id=project.workspace_id,
        actor_id=change["actor_id"],
        action=change["action"],
        entity_type="project",
        entity_id=project.id,
        target_user_id=change["target_user_id"],
        before={"role": before_role} if before_role is not None else None,
        after={"role": after_role} if after_role is not None else None,
    )
