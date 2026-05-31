"""Dispatch a committed domain event for side-effect processing."""
from __future__ import annotations

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.events import process_domain_event


async def dispatch_event(event_id: str) -> None:
    if settings.event_mode == "taskiq":
        # Lazy import so the API has no hard dependency on a live broker in inline mode.
        from app.worker import process_domain_event_task

        await process_domain_event_task.kiq(event_id)
    else:
        async with SessionLocal() as db:
            await process_domain_event(db, event_id)
