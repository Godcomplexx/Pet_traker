from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Task, TaskChecklistItem, User
from app.schemas import TaskChecklistItemCreate, TaskChecklistItemOut, TaskChecklistItemUpdate, TaskChecklistReorder
from app.services.realtime import publish_queued_events
from app.services.task_helpers import load_task_with_access, queue_task_live_event

router = APIRouter(tags=["tasks"])


async def _load_checklist_item_with_access(
    db: AsyncSession, item_id: str, user: User
) -> TaskChecklistItem:
    item = await db.get(TaskChecklistItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Checklist item not found")
    await load_task_with_access(db, item.task_id, user)
    return item


@router.get("/tasks/{task_id}/checklist", response_model=list[TaskChecklistItemOut])
async def list_task_checklist(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await load_task_with_access(db, task_id, user)
    rows = await db.scalars(
        select(TaskChecklistItem)
        .where(TaskChecklistItem.task_id == task_id)
        .order_by(TaskChecklistItem.position.asc(), TaskChecklistItem.created_at.asc())
    )
    return rows.all()


@router.post(
    "/tasks/{task_id}/checklist",
    response_model=TaskChecklistItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_checklist_item(
    task_id: str,
    data: TaskChecklistItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await load_task_with_access(db, task_id, user)
    max_position = await db.scalar(
        select(func.max(TaskChecklistItem.position)).where(TaskChecklistItem.task_id == task_id)
    )
    item = TaskChecklistItem(
        task_id=task_id,
        created_by=user.id,
        title=data.title,
        kind=data.kind,
        position=int(max_position or 0) + 1,
    )
    db.add(item)
    queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(item)
    return item


@router.patch("/task-checklist/{item_id}", response_model=TaskChecklistItemOut)
async def update_task_checklist_item(
    item_id: str,
    data: TaskChecklistItemUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _load_checklist_item_with_access(db, item_id, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    task = await db.get(Task, item.task_id)
    if task is not None:
        queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    await db.refresh(item)
    return item


@router.patch("/tasks/{task_id}/checklist/reorder", response_model=list[TaskChecklistItemOut])
async def reorder_task_checklist(
    task_id: str,
    data: TaskChecklistReorder,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await load_task_with_access(db, task_id, user)
    if data.order:
        rows = await db.scalars(select(TaskChecklistItem).where(TaskChecklistItem.task_id == task_id))
        items = {item.id: item for item in rows.all()}
        for idx, item_id in enumerate(data.order):
            if item_id in items:
                items[item_id].position = idx
    queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    rows = await db.scalars(
        select(TaskChecklistItem)
        .where(TaskChecklistItem.task_id == task_id)
        .order_by(TaskChecklistItem.position.asc(), TaskChecklistItem.created_at.asc())
    )
    return rows.all()


@router.delete("/task-checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task_checklist_item(
    item_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await _load_checklist_item_with_access(db, item_id, user)
    task = await db.get(Task, item.task_id)
    await db.delete(item)
    if task is not None:
        queue_task_live_event(db, "task.checklist_updated", task)
    await db.commit()
    await publish_queued_events(db)
    return None
