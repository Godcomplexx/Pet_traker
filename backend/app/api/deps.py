from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import ACCESS, decode_token, hash_api_token
from app.enums import WorkspaceRole
from app.models import ApiToken, User, WorkspaceMember

bearer = HTTPBearer(auto_error=True)

# Roles allowed to mutate team content (create/edit projects, articles, team tasks, comments).
WRITE_ROLES = {
    WorkspaceRole.OWNER,
    WorkspaceRole.ADMIN,
    WorkspaceRole.PROJECT_LEAD,
    WorkspaceRole.EDITOR,
    WorkspaceRole.MEMBER,
}
# Roles that may close other members' team tasks / manage status.
ELEVATED_ROLES = {
    WorkspaceRole.OWNER,
    WorkspaceRole.ADMIN,
    WorkspaceRole.PROJECT_LEAD,
    WorkspaceRole.EDITOR,
}
ADMIN_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_id = decode_token(creds.credentials, ACCESS)
    except ValueError:
        token_hash = hash_api_token(creds.credentials)
        api_token = await db.scalar(
            select(ApiToken).where(
                ApiToken.token_hash == token_hash,
                ApiToken.revoked_at.is_(None),
            )
        )
        if api_token is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
        user = await db.get(User, api_token.user_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
        api_token.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return user
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


async def require_membership(
    workspace_id: str, db: AsyncSession, user: User
) -> WorkspaceMember:
    """Return the caller's membership in the workspace or 403/404. Never leaks foreign data."""
    member = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if member is None:
        # Do not distinguish "not a member" from "does not exist" — avoids leaking existence.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")
    return member
