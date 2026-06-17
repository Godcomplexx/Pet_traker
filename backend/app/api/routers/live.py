from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_membership
from app.core.database import get_db
from app.core.security import ACCESS, decode_token
from app.enums import TaskScope
from app.models import Task, User, WorkspaceMember
from app.services.realtime import can_receive, hub, make_event, publish_live_event

router = APIRouter(tags=["live"])


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _user_from_token(token: str, db: AsyncSession) -> User:
    try:
        user_id = decode_token(token, ACCESS)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


@router.get("/live/events")
async def live_events(token: str = Query(min_length=1), db: AsyncSession = Depends(get_db)):
    user = await _user_from_token(token, db)
    workspace_ids = set(
        (
            await db.scalars(
                select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user.id)
            )
        ).all()
    )
    queue = hub.subscribe()

    async def stream():
        try:
            yield _sse("live.ready", {"user_id": user.id, "workspace_ids": list(workspace_ids)})
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=20)
                    if can_receive(event, user_id=user.id, workspace_ids=workspace_ids):
                        yield _sse(event["type"], event)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            hub.unsubscribe(queue)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tasks/{task_id}/typing", status_code=status.HTTP_204_NO_CONTENT)
async def task_typing(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if task is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.scope == TaskScope.PERSONAL:
        if task.owner_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
        workspace_id = None
        target_user_ids = [task.owner_id]
    else:
        await require_membership(task.workspace_id, db, user)
        workspace_id = task.workspace_id
        target_user_ids = []
    await publish_live_event(
        make_event(
            "task.typing",
            {"task_id": task_id, "user_id": user.id, "display_name": user.display_name},
            workspace_id=workspace_id,
            target_user_ids=target_user_ids,
        )
    )
    return None
