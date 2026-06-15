from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.config import settings
from app.core.database import get_db
from app.enums import TaskScope
from app.models import Article, Attachment, Project, Task, User
from app.schemas import AttachmentOut
from app.services.realtime import make_event, publish_live_event

router = APIRouter(tags=["attachments"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "text/csv",
    "text/plain",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".csv",
    ".txt",
    ".xls",
    ".xlsx",
    ".doc",
    ".docx",
}
IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


def _upload_root() -> Path:
    root = Path(settings.upload_dir).expanduser()
    if not root.is_absolute():
        root = Path.cwd() / root
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _safe_original_name(name: str | None) -> str:
    raw = Path(name or "attachment").name.strip() or "attachment"
    return re.sub(r"[\x00-\x1f<>:\"/\\|?*]", "_", raw)[:300]


def _validate_file_meta(file: UploadFile, original_name: str) -> None:
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported file extension")
    if (file.content_type or "application/octet-stream") not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unsupported file type")


async def _read_limited(file: UploadFile) -> bytes:
    data = await file.read(settings.upload_max_bytes + 1)
    if len(data) > settings.upload_max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File is too large")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    return data


def _to_out(att: Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=att.id,
        workspace_id=att.workspace_id,
        task_id=att.task_id,
        project_id=att.project_id,
        article_id=att.article_id,
        uploaded_by=att.uploaded_by,
        original_name=att.original_name,
        content_type=att.content_type,
        size_bytes=att.size_bytes,
        version=att.version,
        download_url=f"/api/attachments/{att.id}/download",
        created_at=att.created_at,
    )


async def _publish_attachment_event(
    type_: str,
    att: Attachment | None,
    task: Task | None = None,
    payload: dict | None = None,
    workspace_id: str | None = None,
) -> None:
    if att is not None:
        payload = {
            "attachment_id": att.id,
            "task_id": att.task_id,
            "project_id": att.project_id,
            "article_id": att.article_id,
        }
        workspace_id = att.workspace_id
    payload = payload or {}
    if task is not None and task.scope == TaskScope.PERSONAL:
        await publish_live_event(make_event(type_, payload, target_user_ids=[task.owner_id]))
    else:
        await publish_live_event(make_event(type_, payload, workspace_id=workspace_id))


async def _task_with_access(db: AsyncSession, task_id: str, user: User) -> Task:
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    else:
        await require_membership(task.workspace_id, db, user)
    return task


async def _project_with_access(db: AsyncSession, project_id: str, user: User) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await require_membership(project.workspace_id, db, user)
    return project


async def _article_with_access(db: AsyncSession, article_id: str, user: User) -> Article:
    article = await db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    await require_membership(article.workspace_id, db, user)
    return article


async def _attachment_with_access(db: AsyncSession, attachment_id: str, user: User) -> Attachment:
    att = await db.get(Attachment, attachment_id)
    if att is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    if att.task_id:
        await _task_with_access(db, att.task_id, user)
    elif att.project_id:
        await _project_with_access(db, att.project_id, user)
    elif att.article_id:
        await _article_with_access(db, att.article_id, user)
    else:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attachment not found")
    return att


async def _create_attachment(
    *,
    db: AsyncSession,
    user: User,
    file: UploadFile,
    workspace_id: str | None,
    task_id: str | None = None,
    project_id: str | None = None,
    article_id: str | None = None,
) -> Attachment:
    original_name = _safe_original_name(file.filename)
    _validate_file_meta(file, original_name)
    data = await _read_limited(file)
    root = _upload_root()
    stored_name = f"{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
    path = (root / stored_name).resolve()
    if root not in path.parents:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid storage path")
    path.write_bytes(data)

    existing_version = await db.scalar(
        select(func.max(Attachment.version)).where(
            Attachment.task_id == task_id,
            Attachment.project_id == project_id,
            Attachment.article_id == article_id,
            Attachment.original_name == original_name,
        )
    )
    att = Attachment(
        workspace_id=workspace_id,
        task_id=task_id,
        project_id=project_id,
        article_id=article_id,
        uploaded_by=user.id,
        original_name=original_name,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(data),
        version=int(existing_version or 0) + 1,
        storage_path=str(path),
    )
    db.add(att)
    await db.commit()
    await db.refresh(att)
    return att


@router.get("/tasks/{task_id}/attachments", response_model=list[AttachmentOut])
async def list_task_attachments(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _task_with_access(db, task_id, user)
    rows = await db.scalars(
        select(Attachment).where(Attachment.task_id == task_id).order_by(Attachment.created_at.desc())
    )
    return [_to_out(att) for att in rows.all()]


@router.post("/tasks/{task_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_task_attachment(
    task_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _task_with_access(db, task_id, user)
    att = await _create_attachment(
        db=db,
        user=user,
        file=file,
        workspace_id=task.workspace_id,
        task_id=task.id,
    )
    await _publish_attachment_event("attachment.created", att, task)
    return _to_out(att)


@router.get("/projects/{project_id}/attachments", response_model=list[AttachmentOut])
async def list_project_attachments(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _project_with_access(db, project_id, user)
    rows = await db.scalars(
        select(Attachment).where(Attachment.project_id == project_id).order_by(Attachment.created_at.desc())
    )
    return [_to_out(att) for att in rows.all()]


@router.post("/projects/{project_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_project_attachment(
    project_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _project_with_access(db, project_id, user)
    att = await _create_attachment(
        db=db,
        user=user,
        file=file,
        workspace_id=project.workspace_id,
        project_id=project.id,
    )
    await _publish_attachment_event("attachment.created", att)
    return _to_out(att)


@router.get("/articles/{article_id}/attachments", response_model=list[AttachmentOut])
async def list_article_attachments(
    article_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _article_with_access(db, article_id, user)
    rows = await db.scalars(
        select(Attachment).where(Attachment.article_id == article_id).order_by(Attachment.created_at.desc())
    )
    return [_to_out(att) for att in rows.all()]


@router.post("/articles/{article_id}/attachments", response_model=AttachmentOut, status_code=201)
async def upload_article_attachment(
    article_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    article = await _article_with_access(db, article_id, user)
    att = await _create_attachment(
        db=db,
        user=user,
        file=file,
        workspace_id=article.workspace_id,
        article_id=article.id,
    )
    await _publish_attachment_event("attachment.created", att)
    return _to_out(att)


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    att = await _attachment_with_access(db, attachment_id, user)
    path = Path(att.storage_path)
    if not path.exists() or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    disposition = "inline" if att.content_type in IMAGE_CONTENT_TYPES or att.content_type == "application/pdf" else "attachment"
    return FileResponse(
        path,
        media_type=att.content_type,
        filename=att.original_name,
        content_disposition_type=disposition,
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    att = await _attachment_with_access(db, attachment_id, user)
    path = Path(att.storage_path)
    task = await db.get(Task, att.task_id) if att.task_id else None
    workspace_id = att.workspace_id
    task_id = att.task_id
    project_id = att.project_id
    article_id = att.article_id
    await db.delete(att)
    await db.commit()
    await _publish_attachment_event(
        "attachment.deleted",
        None,
        task,
        payload={
            "attachment_id": attachment_id,
            "task_id": task_id,
            "project_id": project_id,
            "article_id": article_id,
        },
        workspace_id=workspace_id,
    )
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        pass
    return None
