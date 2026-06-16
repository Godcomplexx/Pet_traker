"""Schemas for public API integrations: API tokens, webhooks, CSV imports."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas_core import ORMModel


class ApiTokenCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class ApiTokenOut(ORMModel):
    id: str
    name: str
    token_prefix: str
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime


class ApiTokenCreated(ApiTokenOut):
    token: str


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: list[str] = Field(default_factory=lambda: ["*"])

    @field_validator("events")
    @classmethod
    def normalize_events(cls, value: list[str]) -> list[str]:
        events = [str(item).strip().upper() for item in value if str(item).strip()]
        return list(dict.fromkeys(events or ["*"]))


class WebhookOut(ORMModel):
    id: str
    workspace_id: str
    url: str
    active: bool
    events: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WebhookCreated(WebhookOut):
    secret: str


class WebhookDeliveryOut(ORMModel):
    id: str
    subscription_id: str
    workspace_id: str
    event_id: str | None = None
    event_type: str
    payload: dict
    status: str
    attempts: int
    last_error: str | None = None
    created_at: datetime
    delivered_at: datetime | None = None


class ImportTasksOut(BaseModel):
    created: int
    task_ids: list[str] = Field(default_factory=list)
