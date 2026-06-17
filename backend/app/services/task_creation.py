from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import WRITE_ROLES
from app.enums import TaskScope, TaskType, TaskVisibility
from app.models import Article, Project, Task, User
from app.schemas import TaskCreate
from app.services.audit import record_audit, snapshot_fields
from app.services.notifications import notify_assignment
from app.services.realtime import publish_queued_events
from app.services.task_helpers import (
    TASK_AUDIT_FIELDS,
    assert_member,
    queue_task_live_event,
    validate_workspace_assignees,
)


async def create_task_for_user(db: AsyncSession, data: TaskCreate, user: User) -> Task:
    if data.scope == TaskScope.PERSONAL:
        return await _create_personal_task(db, data, user)

    workspace_id, project_id, article_id, visibility = await _resolve_team_scope(db, data)
    member = await assert_member(db, workspace_id, user)
    if member.role not in WRITE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")

    assignee_ids = await validate_workspace_assignees(
        db,
        workspace_id,
        [*(data.assignee_ids or []), *([data.assignee_id] if data.assignee_id else [])],
    )
    task = Task(
        workspace_id=workspace_id,
        project_id=project_id,
        article_id=article_id,
        owner_id=user.id,
        created_by=user.id,
        assignee_id=assignee_ids[0] if assignee_ids else None,
        assignees=assignee_ids,
        title=data.title,
        description=data.description,
        scope=data.scope,
        visibility=visibility,
        type=data.type,
        priority=data.priority,
        due_date=data.due_date,
    )
    db.add(task)
    await db.flush()
    record_audit(
        db,
        workspace_id=workspace_id,
        actor_id=user.id,
        action="task.created",
        entity_type="task",
        entity_id=task.id,
        after=snapshot_fields(task, TASK_AUDIT_FIELDS),
    )
    for assignee_id in assignee_ids:
        await notify_assignment(
            db,
            assignee_id=assignee_id,
            actor_id=user.id,
            workspace_id=workspace_id,
            task_id=task.id,
            title=task.title,
        )
    queue_task_live_event(db, "task.created", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(task)
    return task


async def _create_personal_task(db: AsyncSession, data: TaskCreate, user: User) -> Task:
    task = Task(
        owner_id=user.id,
        created_by=user.id,
        assignee_id=user.id,
        title=data.title,
        description=data.description,
        scope=TaskScope.PERSONAL,
        visibility=TaskVisibility.PRIVATE,
        type=data.type if data.type != TaskType.OTHER else TaskType.PERSONAL,
        priority=data.priority,
        due_date=data.due_date,
    )
    db.add(task)
    await db.flush()
    queue_task_live_event(db, "task.created", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(task)
    return task


async def _resolve_team_scope(db: AsyncSession, data: TaskCreate):
    workspace_id = data.workspace_id
    project_id = None
    article_id = None
    visibility = TaskVisibility.WORKSPACE

    if data.scope == TaskScope.PROJECT:
        if not data.project_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "project_id required for PROJECT scope")
        project = await db.get(Project, data.project_id)
        if project is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        project_id = project.id
        workspace_id = project.workspace_id
        visibility = TaskVisibility.PROJECT
    elif data.scope == TaskScope.ARTICLE:
        if not data.article_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "article_id required for ARTICLE scope")
        article = await db.get(Article, data.article_id)
        if article is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
        article_id = article.id
        workspace_id = article.workspace_id
        visibility = TaskVisibility.ARTICLE
    elif not workspace_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "workspace_id required for WORKSPACE scope")

    return workspace_id, project_id, article_id, visibility
