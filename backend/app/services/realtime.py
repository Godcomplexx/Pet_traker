from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


LiveEvent = dict[str, Any]


class LiveHub:
    """Small in-process pub/sub hub for SSE clients.

    This is intentionally process-local. It gives the product real-time UX in
    dev/MVP deployments; multi-worker production can replace the publish layer
    with Redis without changing the browser contract.
    """

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[LiveEvent]] = set()

    def subscribe(self) -> asyncio.Queue[LiveEvent]:
        queue: asyncio.Queue[LiveEvent] = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LiveEvent]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: LiveEvent) -> None:
        stale: list[asyncio.Queue[LiveEvent]] = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                stale.append(queue)
        for queue in stale:
            self.unsubscribe(queue)


hub = LiveHub()


def make_event(
    type_: str,
    payload: dict[str, Any] | None = None,
    *,
    workspace_id: str | None = None,
    target_user_ids: Iterable[str] | None = None,
) -> LiveEvent:
    return {
        "type": type_,
        "payload": payload or {},
        "workspace_id": workspace_id,
        "target_user_ids": list(dict.fromkeys(target_user_ids or [])),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def queue_live_event(db: AsyncSession, event: LiveEvent) -> None:
    db.info.setdefault("live_events", []).append(event)


async def publish_queued_events(db: AsyncSession) -> None:
    events = db.info.pop("live_events", [])
    for event in events:
        await hub.publish(event)


async def publish_live_event(event: LiveEvent) -> None:
    await hub.publish(event)


def can_receive(event: LiveEvent, *, user_id: str, workspace_ids: set[str]) -> bool:
    target_user_ids = set(event.get("target_user_ids") or [])
    if user_id in target_user_ids:
        return True
    workspace_id = event.get("workspace_id")
    return bool(workspace_id and workspace_id in workspace_ids)


async def matching_events(
    queue: asyncio.Queue[LiveEvent],
    *,
    user_id: str,
    workspace_ids: set[str],
) -> AsyncIterator[LiveEvent]:
    while True:
        event = await queue.get()
        if can_receive(event, user_id=user_id, workspace_ids=workspace_ids):
            yield event
