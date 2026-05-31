"""Reward calculation (spec §14). Pure functions — no DB access here."""
from __future__ import annotations

from app.enums import ArticleStatus, DomainEventType, ProjectStatus


def level_of(total_xp: int) -> int:
    """MVP level formula: level = floor(total_xp / 100) + 1."""
    return total_xp // 100 + 1


def reward_for_event(event_type: DomainEventType, payload: dict) -> int:
    """Return XP to grant for a processed domain event. 0 means no reward."""
    if event_type == DomainEventType.TASK_COMPLETED:
        xp = 5 if payload.get("scope") == "PERSONAL" else 10
        if payload.get("before_due"):
            xp += 5
        return xp

    if event_type == DomainEventType.PROJECT_STATUS_CHANGED:
        return 50 if payload.get("status") == ProjectStatus.DONE.value else 0

    if event_type == DomainEventType.ARTICLE_STATUS_CHANGED:
        return {
            ArticleStatus.SUBMITTED.value: 50,
            ArticleStatus.ACCEPTED.value: 100,
            ArticleStatus.PUBLISHED.value: 150,
        }.get(payload.get("status"), 0)

    if event_type == DomainEventType.COMMENT_ADDED:
        return 1

    return 0
