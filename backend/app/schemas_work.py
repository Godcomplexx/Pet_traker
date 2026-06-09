"""Pydantic schemas for articles, tasks, comments, notifications, and wall posts."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app import enums
from app.schemas_core import ORMModel


# ── Article ──
class ArticleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    project_id: str | None = None
    target_journal: str | None = None
    document_url: str | None = None
    deadline: date | None = None


class ArticleStatusUpdate(BaseModel):
    status: enums.ArticleStatus


class ArticleOut(ORMModel):
    id: str
    workspace_id: str
    project_id: str | None = None
    title: str
    description: str | None = None
    status: enums.ArticleStatus
    owner_id: str
    target_journal: str | None = None
    document_url: str | None = None
    deadline: date | None = None
    position: int = 0
    created_at: datetime
    # Богатые поля для карточек доски.
    task_total: int | None = None
    task_done: int | None = None
    member_ids: list[str] = Field(default_factory=list)


# ── Task ──
class TaskCreate(BaseModel):
    scope: enums.TaskScope
    workspace_id: str | None = None
    project_id: str | None = None
    article_id: str | None = None
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    type: enums.TaskType = enums.TaskType.OTHER
    priority: enums.TaskPriority = enums.TaskPriority.MEDIUM
    assignee_id: str | None = None
    # Несколько исполнителей (если задано — имеет приоритет над assignee_id).
    assignee_ids: list[str] = Field(default_factory=list)
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    description: str | None = None
    type: enums.TaskType | None = None
    priority: enums.TaskPriority | None = None
    status: enums.TaskStatus | None = None
    assignee_id: str | None = None
    assignee_ids: list[str] | None = None
    due_date: date | None = None


class TaskOut(ORMModel):
    id: str
    workspace_id: str | None = None
    project_id: str | None = None
    article_id: str | None = None
    owner_id: str
    title: str
    description: str | None = None
    scope: enums.TaskScope
    visibility: enums.TaskVisibility
    status: enums.TaskStatus
    type: enums.TaskType
    priority: enums.TaskPriority
    assignee_id: str | None = None
    assignees: list[str] = Field(default_factory=list)
    due_date: date | None = None
    completed_at: datetime | None = None
    completed_by: str | None = None
    position: int = 0
    created_at: datetime


# ── Comment ──
class CommentCreate(BaseModel):
    text: str = Field(min_length=1)
    # Explicit mention targets (resolved against workspace members). Plus any
    # `@email` tokens found in `text` are parsed automatically.
    mention_user_ids: list[str] = Field(default_factory=list)


class CommentUpdate(BaseModel):
    text: str = Field(min_length=1)


class CommentOut(ORMModel):
    id: str
    author_id: str
    text: str
    created_at: datetime


# ── Activity / notifications / pet feed ──
class ActivityOut(ORMModel):
    id: str
    actor_id: str
    event_type: str
    entity_type: str
    entity_id: str
    text: str
    created_at: datetime


class NotificationOut(ORMModel):
    id: str
    type: enums.NotificationType
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool
    created_at: datetime


class WallPostCreate(BaseModel):
    text: str = Field(default="", max_length=2000)
    image_data: str | None = Field(default=None, max_length=700_000)

    @field_validator("image_data")
    @classmethod
    def check_wall_image(cls, v: str | None) -> str | None:
        if not v:
            return None
        allowed = (
            "data:image/png;base64,",
            "data:image/jpeg;base64,",
            "data:image/webp;base64,",
            "data:image/gif;base64,",
        )
        if v.startswith(allowed):
            return v
        parsed = urlparse(v)
        if parsed.scheme == "https" and re.search(r"\.(png|jpe?g|webp|gif)(\?.*)?$", parsed.path, re.I):
            return v
        raise ValueError("Можно прикрепить только png, jpg, webp или gif")


class WallReactionIn(BaseModel):
    emoji: str = Field(min_length=1, max_length=16)

    @field_validator("emoji")
    @classmethod
    def check_emoji(cls, v: str) -> str:
        allowed = {"👍", "👎", "❤️", "😂", "🎉", "👀", "🔥"}
        if v not in allowed:
            raise ValueError("Недоступная реакция")
        return v


class WallPostOut(BaseModel):
    id: str
    author_id: str
    author_name: str
    text: str
    image_data: str | None = None
    reactions: dict[str, int] = Field(default_factory=dict)
    my_reactions: list[str] = Field(default_factory=list)
    created_at: datetime


class RpsInviteIn(BaseModel):
    opponent_id: str
    choice: str = Field(pattern="^(rock|paper|scissors)$")


class RpsRespondIn(BaseModel):
    accept: bool


class RpsChoiceIn(BaseModel):
    choice: str = Field(pattern="^(rock|paper|scissors)$")


class RpsChallengeOut(ORMModel):
    id: str
    workspace_id: str
    challenger_id: str
    opponent_id: str
    status: str
    challenger_choice: str | None = None
    opponent_choice: str | None = None
    winner_id: str | None = None
    reward_awarded: bool = False
    created_at: datetime
    responded_at: datetime | None = None
    completed_at: datetime | None = None
