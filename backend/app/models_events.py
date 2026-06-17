from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app import enums
from app.core.database import Base
from app.models_common import JsonType, PK, TS, _now


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (UniqueConstraint("source_event_id", "user_id", "reward_type", name="uq_reward_event"),)

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    source_event_id: Mapped[str] = mapped_column(ForeignKey("domain_events.id", ondelete="CASCADE"))
    xp_amount: Mapped[int] = mapped_column(Integer, default=0)
    reward_type: Mapped[enums.RewardType] = mapped_column(SAEnum(enums.RewardType), default=enums.RewardType.XP)
    privacy_level: Mapped[enums.PrivacyLevel] = mapped_column(SAEnum(enums.PrivacyLevel), default=enums.PrivacyLevel.WORKSPACE)
    item_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = TS()


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict] = mapped_column("metadata", JsonType, default=dict)
    visibility: Mapped[enums.TaskVisibility] = mapped_column(SAEnum(enums.TaskVisibility), default=enums.TaskVisibility.WORKSPACE)
    created_at: Mapped[datetime] = TS()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    before: Mapped[dict] = mapped_column(JsonType, default=dict)
    after: Mapped[dict] = mapped_column(JsonType, default=dict)
    details: Mapped[dict] = mapped_column(JsonType, default=dict)
    created_at: Mapped[datetime] = TS()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[enums.NotificationType] = mapped_column(SAEnum(enums.NotificationType))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = TS()


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id: Mapped[str] = PK()
    event_type: Mapped[enums.DomainEventType] = mapped_column(SAEnum(enums.DomainEventType))
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    privacy_level: Mapped[enums.PrivacyLevel] = mapped_column(SAEnum(enums.PrivacyLevel), default=enums.PrivacyLevel.WORKSPACE)
    payload: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[enums.EventStatus] = mapped_column(SAEnum(enums.EventStatus), default=enums.EventStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = TS()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    events: Mapped[list] = mapped_column(JsonType, default=list)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = PK()
    subscription_id: Mapped[str] = mapped_column(ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("domain_events.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = TS()
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
