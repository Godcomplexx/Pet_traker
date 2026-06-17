from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ADMIN_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.enums import WorkspaceRole
from app.models import User, Workspace, WorkspaceMember
from app.schemas import (
    MemberInvite,
    MemberOut,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceJoin,
    WorkspaceOut,
)
from app.services.audit import record_audit
from app.services.demo_data import seed_workspace_demo

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    ws = Workspace(name=data.name, description=data.description, owner_id=user.id)
    db.add(ws)
    await db.flush()
    # FR-WS-2: creator becomes OWNER.
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.OWNER))
    record_audit(
        db,
        workspace_id=ws.id,
        actor_id=user.id,
        action="workspace.created",
        entity_type="workspace",
        entity_id=ws.id,
        after={"name": ws.name, "description": ws.description, "owner_id": user.id},
        target_user_id=user.id,
    )
    if data.with_demo_data:
        await seed_workspace_demo(db, workspace_id=ws.id, user_id=user.id)
    await db.commit()
    await db.refresh(ws)
    return ws


@router.post("/join", response_model=WorkspaceOut)
async def join_workspace(
    data: WorkspaceJoin, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Присоединиться к лаборатории по коду приглашения. Новый участник — MEMBER."""
    ws = await db.scalar(select(Workspace).where(Workspace.join_code == data.join_code))
    if ws is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Лаборатория с таким кодом не найдена")

    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Вы уже участник этой лаборатории")

    db.add(WorkspaceMember(workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.MEMBER))
    record_audit(
        db,
        workspace_id=ws.id,
        actor_id=user.id,
        action="workspace.member_joined",
        entity_type="workspace",
        entity_id=ws.id,
        target_user_id=user.id,
        after={"role": WorkspaceRole.MEMBER},
    )
    await db.commit()
    await db.refresh(ws)
    return ws


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # FR-WS-4: only workspaces the user belongs to.
    rows = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == user.id)
    )
    return rows.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await require_membership(workspace_id, db, user)
    return await db.get(Workspace, workspace_id)


@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(
    workspace_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    await require_membership(workspace_id, db, user)
    rows = await db.execute(
        select(WorkspaceMember, User.display_name, User.email)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at)
    )
    out = []
    for member, display_name, email in rows.all():
        out.append(
            MemberOut(
                id=member.id,
                user_id=member.user_id,
                role=member.role,
                joined_at=member.joined_at,
                display_name=display_name,
                email=email,
            )
        )
    return out


@router.post("/{workspace_id}/invite", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: str,
    data: MemberInvite,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in ADMIN_ROLES:  # FR-WS-3
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only OWNER/ADMIN can add members")
    if data.role == WorkspaceRole.OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot assign owner role")

    invitee = await db.scalar(select(User).where(User.email == data.email))
    if invitee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that email")

    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == invitee.id,
        )
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member")

    new_member = WorkspaceMember(workspace_id=workspace_id, user_id=invitee.id, role=data.role)
    db.add(new_member)
    await db.flush()
    record_audit(
        db,
        workspace_id=workspace_id,
        actor_id=user.id,
        action="workspace.member_invited",
        entity_type="workspace",
        entity_id=workspace_id,
        target_user_id=invitee.id,
        after={"role": data.role},
    )
    await db.commit()
    await db.refresh(new_member)
    return new_member


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberOut)
async def update_member_role(
    workspace_id: str,
    user_id: str,
    data: MemberRoleUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    actor = await require_membership(workspace_id, db, user)
    if actor.role not in ADMIN_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only OWNER/ADMIN can change roles")
    target = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
        )
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if target.role == WorkspaceRole.OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot change owner role")
    if data.role == WorkspaceRole.OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot assign owner role")
    before_role = target.role
    target.role = data.role
    record_audit(
        db,
        workspace_id=workspace_id,
        actor_id=user.id,
        action="workspace.member_role_changed",
        entity_type="workspace",
        entity_id=workspace_id,
        target_user_id=user_id,
        before={"role": before_role},
        after={"role": data.role},
    )
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    workspace_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    actor = await require_membership(workspace_id, db, user)
    if actor.role not in ADMIN_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only OWNER/ADMIN can remove members")
    target = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
        )
    )
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    if target.role == WorkspaceRole.OWNER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot remove the owner")
    record_audit(
        db,
        workspace_id=workspace_id,
        actor_id=user.id,
        action="workspace.member_removed",
        entity_type="workspace",
        entity_id=workspace_id,
        target_user_id=user_id,
        before={"role": target.role},
    )
    await db.delete(target)
    await db.commit()
    return None
