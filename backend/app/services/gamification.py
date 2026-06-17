"""Reward calculation (spec §14). Pure functions — no DB access here."""
from __future__ import annotations

from app.enums import ArticleStatus, DomainEventType, ProjectStatus

TASK_TEAM_XP = 10
TASK_PERSONAL_XP = 5
TASK_BEFORE_DUE_BONUS_XP = 5
PROJECT_DONE_XP = 50
ARTICLE_SUBMITTED_XP = 50
ARTICLE_ACCEPTED_XP = 100
ARTICLE_PUBLISHED_XP = 150
COMMENT_XP = 1
COMMENT_DAILY_CAP = 5
LEVEL_UP_COINS = 10

DAILY_LOGIN_COINS = 30
SUDOKU_COINS = 50
ZIP_COINS = 45
MINESWEEPER_COINS = 55
RPS_WIN_COINS = 5


def level_of(total_xp: int) -> int:
    """MVP level formula: level = floor(total_xp / 100) + 1."""
    return total_xp // 100 + 1


def reward_for_event(event_type: DomainEventType, payload: dict) -> int:
    """Return XP to grant for a processed domain event. 0 means no reward."""
    if event_type == DomainEventType.TASK_COMPLETED:
        xp = TASK_PERSONAL_XP if payload.get("scope") == "PERSONAL" else TASK_TEAM_XP
        if payload.get("before_due"):
            xp += TASK_BEFORE_DUE_BONUS_XP
        return xp

    if event_type == DomainEventType.PROJECT_STATUS_CHANGED:
        return PROJECT_DONE_XP if payload.get("status") == ProjectStatus.DONE.value else 0

    if event_type == DomainEventType.ARTICLE_STATUS_CHANGED:
        return {
            ArticleStatus.SUBMITTED.value: ARTICLE_SUBMITTED_XP,
            ArticleStatus.ACCEPTED.value: ARTICLE_ACCEPTED_XP,
            ArticleStatus.PUBLISHED.value: ARTICLE_PUBLISHED_XP,
        }.get(payload.get("status"), 0)

    if event_type == DomainEventType.COMMENT_ADDED:
        return COMMENT_XP

    return 0


def reward_rules() -> dict:
    return {
        "xp": {
            "task_completed": {
                "team": TASK_TEAM_XP,
                "personal": TASK_PERSONAL_XP,
                "before_due_bonus": TASK_BEFORE_DUE_BONUS_XP,
            },
            "project_status": {ProjectStatus.DONE.value: PROJECT_DONE_XP},
            "article_status": {
                ArticleStatus.SUBMITTED.value: ARTICLE_SUBMITTED_XP,
                ArticleStatus.ACCEPTED.value: ARTICLE_ACCEPTED_XP,
                ArticleStatus.PUBLISHED.value: ARTICLE_PUBLISHED_XP,
            },
            "comment_added": {
                "amount": COMMENT_XP,
                "daily_cap": COMMENT_DAILY_CAP,
                "window_hours": 24,
            },
        },
        "coins": {
            "level_up_per_level": LEVEL_UP_COINS,
            "daily_login": DAILY_LOGIN_COINS,
            "daily_games": {
                "sudoku": SUDOKU_COINS,
                "zip": ZIP_COINS,
                "minesweeper": MINESWEEPER_COINS,
            },
            "rps_win": RPS_WIN_COINS,
        },
        "care": {
            "team_task": {"hunger": 12, "energy": 6, "mood": 8},
            "personal_task": {"hunger": 8, "energy": 6, "mood": 8},
            "milestone": {"hunger": 20, "energy": 6, "mood": 18},
        },
        "settings": {
            "gamification_muted": "Keeps rewards and pet state, but lets clients hide celebratory UI.",
        },
    }
