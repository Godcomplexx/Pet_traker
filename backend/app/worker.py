"""Taskiq broker + worker tasks.

Run the worker (production async path) with:
    taskiq worker app.worker:broker
and set EVENT_MODE=taskiq so the API enqueues events instead of processing inline.
"""
from __future__ import annotations

from taskiq_redis import ListQueueBroker

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Pet
from app.services.deadlines import run_deadline_check
from app.services.events import process_domain_event
from app.services.pet import apply_decay

broker = ListQueueBroker(settings.redis_url)


@broker.task
async def process_domain_event_task(event_id: str) -> None:
    async with SessionLocal() as db:
        await process_domain_event(db, event_id)


@broker.task(schedule=[{"cron": "0 8 * * *"}])  # daily 08:00 — needs taskiq scheduler
async def check_deadlines() -> int:
    async with SessionLocal() as db:
        return await run_deadline_check(db)


@broker.task(schedule=[{"cron": "0 * * * *"}])  # hourly — tamagotchi decay tick
async def tick_pets() -> int:
    """Фоновая деградация показателей у всех питомцев (чтобы «жили» без вкладки)."""
    async with SessionLocal() as db:
        pets = (await db.scalars(select(Pet))).all()
        for pet in pets:
            apply_decay(pet)
        await db.commit()
        return len(pets)
