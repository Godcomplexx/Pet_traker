from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ADMIN_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogOut

router = APIRouter(tags=["audit"])


@router.get("/workspaces/{workspace_id}/audit-log", response_model=list[AuditLogOut])
async def list_audit_log(
    workspace_id: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in ADMIN_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only OWNER/ADMIN can view audit log")

    stmt = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit)
    rows = await db.scalars(stmt)
    return rows.all()
