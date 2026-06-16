"""Domain-event emission + idempotent processing (spec §11.14, §15, §18)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import (
    DomainEventType,
    EventStatus,
    PrivacyLevel,
    RewardType,
    TaskVisibility,
)
from app.models import ActivityEvent, DomainEvent, Pet, Reward, WebhookDelivery, WebhookSubscription
from app.services.gamification import level_of, reward_for_event
from app.services.pet import reward_care


@dataclass(frozen=True)
class DomainEventInput:
    event_type: DomainEventType
    actor_id: str
    entity_type: str
    entity_id: str
    workspace_id: str | None
    privacy_level: PrivacyLevel
    payload: dict | None = None


async def emit_event(
    db: AsyncSession,
    options: DomainEventInput | None = None,
    **event_kwargs,
) -> DomainEvent:
    """Create a PENDING domain event. Flushed (not committed) so it shares the caller's txn."""
    data = options or DomainEventInput(**event_kwargs)
    event = DomainEvent(
        event_type=data.event_type,
        actor_id=data.actor_id,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        workspace_id=data.workspace_id,
        privacy_level=data.privacy_level,
        payload=data.payload or {},
        status=EventStatus.PENDING,
    )
    db.add(event)
    await db.flush()
    return event


async def process_domain_event(db: AsyncSession, event_id: str) -> None:
    """Idempotently apply side effects of a domain event: reward → pet → activity.

    Safe to run more than once: rewards are guarded by a unique constraint on
    (source_event_id, user_id, reward_type), and we no-op once the event is PROCESSED.
    """
    event = await db.get(DomainEvent, event_id)
    if event is None or event.status == EventStatus.PROCESSED:
        return

    event.status = EventStatus.PROCESSING
    await db.flush()

    try:
        xp = reward_for_event(event.event_type, event.payload)
        beneficiary_id = event.payload.get("beneficiary_id", event.actor_id)

        # AR-4: comment XP is capped at 5 awards per rolling 24h per user.
        if xp > 0 and event.event_type == DomainEventType.COMMENT_ADDED:
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            awarded_today = await db.scalar(
                select(func.count())
                .select_from(Reward)
                .join(DomainEvent, Reward.source_event_id == DomainEvent.id)
                .where(
                    Reward.user_id == beneficiary_id,
                    DomainEvent.event_type == DomainEventType.COMMENT_ADDED,
                    Reward.created_at >= cutoff,
                )
            )
            if (awarded_today or 0) >= 5:
                xp = 0

        if xp > 0:
            existing = await db.scalar(
                select(Reward).where(
                    Reward.source_event_id == event.id,
                    Reward.user_id == beneficiary_id,
                    Reward.reward_type == RewardType.XP,
                )
            )
            if existing is None:
                db.add(
                    Reward(
                        user_id=beneficiary_id,
                        workspace_id=event.workspace_id,
                        source_event_id=event.id,
                        xp_amount=xp,
                        reward_type=RewardType.XP,
                        privacy_level=event.privacy_level,
                    )
                )
                pet = await db.scalar(select(Pet).where(Pet.user_id == beneficiary_id))
                if pet is not None:
                    level_before = pet.level
                    pet.xp += xp
                    pet.level = level_of(pet.xp)
                    # Монеты за каждый новый уровень (10 монет/уровень) — для магазина/кейсов.
                    if pet.level > level_before:
                        pet.coins = (pet.coins or 0) + (pet.level - level_before) * 10
                    # Тамагочи: работа кормит и радует питомца.
                    milestone = event.event_type in (
                        DomainEventType.PROJECT_STATUS_CHANGED,
                        DomainEventType.ARTICLE_STATUS_CHANGED,
                    )
                    reward_care(pet, scope=event.payload.get("scope", ""), milestone=milestone)

        # Public activity only — never for PRIVATE (personal) events (FR-PT-6, AC-13),
        # and only when the event carries a human-readable line (comments opt out).
        activity_text = event.payload.get("activity_text")
        if event.privacy_level == PrivacyLevel.WORKSPACE and event.workspace_id and activity_text:
            db.add(
                ActivityEvent(
                    workspace_id=event.workspace_id,
                    actor_id=event.actor_id,
                    event_type=event.event_type.value,
                    entity_type=event.entity_type,
                    entity_id=event.entity_id,
                    text=activity_text,
                    visibility=TaskVisibility.WORKSPACE,
                )
            )

        if event.workspace_id:
            hooks = (
                await db.scalars(
                    select(WebhookSubscription).where(
                        WebhookSubscription.workspace_id == event.workspace_id,
                        WebhookSubscription.active.is_(True),
                    )
                )
            ).all()
            for hook in hooks:
                events = set(hook.events or [])
                if "*" not in events and event.event_type.value not in events:
                    continue
                db.add(
                    WebhookDelivery(
                        subscription_id=hook.id,
                        workspace_id=event.workspace_id,
                        event_id=event.id,
                        event_type=event.event_type.value,
                        payload={
                            "event_id": event.id,
                            "event_type": event.event_type.value,
                            "entity_type": event.entity_type,
                            "entity_id": event.entity_id,
                            "workspace_id": event.workspace_id,
                            "payload": event.payload or {},
                            "created_at": event.created_at.isoformat()
                            if event.created_at else None,
                        },
                    )
                )

        event.status = EventStatus.PROCESSED
        event.processed_at = datetime.now(timezone.utc)
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        ev = await db.get(DomainEvent, event_id)
        if ev is not None:
            ev.status = EventStatus.FAILED
            ev.error_message = str(exc)[:500]
            await db.commit()
        raise
