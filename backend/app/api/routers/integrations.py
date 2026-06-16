from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WRITE_ROLES, get_current_user, require_membership
from app.core.database import get_db
from app.core.security import create_api_token, hash_api_token
from app.enums import TaskPriority, TaskScope, TaskStatus, TaskType, TaskVisibility
from app.models import (
    ApiToken,
    Article,
    Project,
    Task,
    User,
    WebhookDelivery,
    WebhookSubscription,
    WorkspaceMember,
)
from app.schemas import (
    ApiTokenCreate,
    ApiTokenCreated,
    ApiTokenOut,
    ImportTasksOut,
    WebhookCreate,
    WebhookCreated,
    WebhookDeliveryOut,
    WebhookOut,
)

router = APIRouter(tags=["integrations"])

MAX_IMPORT_BYTES = 1_000_000


def _csv_response(filename: str, rows: list[dict], fieldnames: list[str]) -> Response:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _parse_date(value: str | None, row_num: int) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid due_date at row {row_num}: expected YYYY-MM-DD",
        )


def _enum(enum_cls, value: str | None, default, row_num: int):
    if not value:
        return default
    try:
        return enum_cls(value.strip().upper())
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid {enum_cls.__name__} at row {row_num}")


@router.post("/api-tokens", response_model=ApiTokenCreated, status_code=status.HTTP_201_CREATED)
async def create_token(
    data: ApiTokenCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = create_api_token()
    model = ApiToken(
        user_id=user.id,
        name=data.name.strip(),
        token_hash=hash_api_token(token),
        token_prefix=token[:12],
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return ApiTokenCreated(**ApiTokenOut.model_validate(model).model_dump(), token=token)


@router.get("/api-tokens", response_model=list[ApiTokenOut])
async def list_tokens(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = await db.scalars(
        select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.created_at.desc())
    )
    return rows.all()


@router.delete("/api-tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await db.get(ApiToken, token_id)
    if token is None or token.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API token not found")
    token.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return None


@router.post(
    "/workspaces/{workspace_id}/webhooks",
    response_model=WebhookCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    workspace_id: str,
    data: WebhookCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    secret = create_api_token().replace("lm_", "whsec_", 1)
    hook = WebhookSubscription(
        workspace_id=workspace_id,
        created_by=user.id,
        url=str(data.url),
        secret_hash=hash_api_token(secret),
        events=data.events,
    )
    db.add(hook)
    await db.commit()
    await db.refresh(hook)
    return WebhookCreated(**WebhookOut.model_validate(hook).model_dump(), secret=secret)


@router.get("/workspaces/{workspace_id}/webhooks", response_model=list[WebhookOut])
async def list_webhooks(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(WebhookSubscription)
        .where(WebhookSubscription.workspace_id == workspace_id)
        .order_by(WebhookSubscription.created_at.desc())
    )
    return rows.all()


@router.delete("/workspaces/{workspace_id}/webhooks/{webhook_id}", status_code=204)
async def disable_webhook(
    workspace_id: str,
    webhook_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    hook = await db.get(WebhookSubscription, webhook_id)
    if hook is None or hook.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Webhook not found")
    hook.active = False
    await db.commit()
    return None


@router.get("/workspaces/{workspace_id}/webhook-deliveries", response_model=list[WebhookDeliveryOut])
async def list_webhook_deliveries(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(WebhookDelivery)
        .where(WebhookDelivery.workspace_id == workspace_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
    )
    return rows.all()


@router.get("/workspaces/{workspace_id}/exports/tasks.csv")
async def export_tasks(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(Task).where(Task.workspace_id == workspace_id).order_by(Task.created_at.asc())
    )
    fields = [
        "id",
        "title",
        "description",
        "scope",
        "status",
        "type",
        "priority",
        "due_date",
        "project_id",
        "article_id",
        "assignee_id",
    ]
    data = [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description or "",
            "scope": task.scope.value,
            "status": task.status.value,
            "type": task.type.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else "",
            "project_id": task.project_id or "",
            "article_id": task.article_id or "",
            "assignee_id": task.assignee_id or "",
        }
        for task in rows.all()
    ]
    return _csv_response("labmate-tasks.csv", data, fields)


@router.get("/workspaces/{workspace_id}/exports/projects.csv")
async def export_projects(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_membership(workspace_id, db, user)
    rows = await db.scalars(
        select(Project).where(Project.workspace_id == workspace_id).order_by(Project.created_at.asc())
    )
    fields = ["id", "name", "description", "type", "status", "deadline", "created_at"]
    data = [
        {
            "id": project.id,
            "name": project.name,
            "description": project.description or "",
            "type": project.type.value,
            "status": project.status.value,
            "deadline": project.deadline.isoformat() if project.deadline else "",
            "created_at": project.created_at.isoformat() if project.created_at else "",
        }
        for project in rows.all()
    ]
    return _csv_response("labmate-projects.csv", data, fields)


@router.post("/workspaces/{workspace_id}/imports/tasks.csv", response_model=ImportTasksOut)
async def import_tasks(
    workspace_id: str,
    file: UploadFile,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member = await require_membership(workspace_id, db, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
    data = await file.read(MAX_IMPORT_BYTES + 1)
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV file is too large")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV must be UTF-8")

    member_ids = set(
        (
            await db.scalars(
                select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
            )
        ).all()
    )
    reader = csv.DictReader(StringIO(text))
    created_ids: list[str] = []

    for row_num, row in enumerate(reader, start=2):
        title = (row.get("title") or "").strip()
        if not title:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Missing title at row {row_num}")

        project_id = (row.get("project_id") or "").strip() or None
        article_id = (row.get("article_id") or "").strip() or None
        scope = TaskScope.WORKSPACE
        visibility = TaskVisibility.WORKSPACE

        if project_id:
            project = await db.get(Project, project_id)
            if project is None or project.workspace_id != workspace_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid project_id at row {row_num}")
            scope = TaskScope.PROJECT
            visibility = TaskVisibility.PROJECT
        if article_id:
            article = await db.get(Article, article_id)
            if article is None or article.workspace_id != workspace_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid article_id at row {row_num}")
            scope = TaskScope.ARTICLE
            visibility = TaskVisibility.ARTICLE

        assignee_id = (row.get("assignee_id") or "").strip() or None
        if assignee_id and assignee_id not in member_ids:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid assignee_id at row {row_num}")

        task = Task(
            workspace_id=workspace_id,
            project_id=project_id,
            article_id=article_id,
            owner_id=user.id,
            created_by=user.id,
            assignee_id=assignee_id,
            assignees=[assignee_id] if assignee_id else [],
            title=title,
            description=(row.get("description") or "").strip() or None,
            scope=scope,
            visibility=visibility,
            status=_enum(TaskStatus, row.get("status"), TaskStatus.TODO, row_num),
            type=_enum(TaskType, row.get("type"), TaskType.OTHER, row_num),
            priority=_enum(TaskPriority, row.get("priority"), TaskPriority.MEDIUM, row_num),
            due_date=_parse_date((row.get("due_date") or "").strip(), row_num),
        )
        db.add(task)
        await db.flush()
        created_ids.append(task.id)

    await db.commit()
    return ImportTasksOut(created=len(created_ids), task_ids=created_ids)
