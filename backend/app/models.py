"""SQLAlchemy ORM models for all PetPro entities (see spec §11)."""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app import enums


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# Код приглашения: 8 символов без похожих 0/O/1/I.
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _join_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


# JSONB on Postgres, falls back to generic JSON elsewhere (tests on sqlite).
JsonType = JSONB().with_variant(__import__("sqlalchemy").JSON(), "sqlite")

PK = lambda: mapped_column(String(36), primary_key=True, default=_uuid)  # noqa: E731
TS = lambda: mapped_column(DateTime(timezone=True), default=_now)  # noqa: E731


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = PK()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Подтверждён ли email кодом из письма.
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    pet: Mapped[Pet | None] = relationship(back_populates="user", uselist=False)


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = TS()


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(80), default="Питомец")
    species: Mapped[str] = mapped_column(String(40), default="capybara")
    # Внешность пиксельного питомца.
    body_color: Mapped[str] = mapped_column(String(9), default="#d99a52")
    accent_color: Mapped[str] = mapped_column(String(9), default="#7a3a22")
    # Прошёл ли пользователь экран создания питомца.
    customized: Mapped[bool] = mapped_column(Boolean, default=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    mood: Mapped[int] = mapped_column(Integer, default=80)
    hunger: Mapped[int] = mapped_column(Integer, default=70)
    energy: Mapped[int] = mapped_column(Integer, default=80)
    # Игровая экономика: монеты + инвентарь купленных/выпавших предметов (список id).
    coins: Mapped[int] = mapped_column(Integer, default=0)
    inventory: Mapped[list] = mapped_column(JsonType, default=list)
    food_inventory: Mapped[dict] = mapped_column(JsonType, default=dict)
    # Экипировано: {type: item_id}, напр. {"hat": "hat_crown", "bg": "bg_space"}.
    equipped: Mapped[dict] = mapped_column(JsonType, default=dict)
    # Момент последнего пересчёта тамагочи-показателей (для decay по времени).
    stats_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="pet")


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = PK()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    # Короткий код для присоединения участников.
    join_code: Mapped[str] = mapped_column(String(12), unique=True, index=True, default=lambda: _join_code())
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    members: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_ws_member"),)

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[enums.WorkspaceRole] = mapped_column(
        SAEnum(enums.WorkspaceRole), default=enums.WorkspaceRole.MEMBER
    )
    joined_at: Mapped[datetime] = TS()

    workspace: Mapped[Workspace] = relationship(back_populates="members")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[enums.ProjectType] = mapped_column(SAEnum(enums.ProjectType), default=enums.ProjectType.OTHER)
    status: Mapped[enums.ProjectStatus] = mapped_column(SAEnum(enums.ProjectStatus), default=enums.ProjectStatus.IDEA)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    members: Mapped[list[ProjectMember]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_proj_member"),)

    id: Mapped[str] = PK()
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[enums.ProjectRole] = mapped_column(SAEnum(enums.ProjectRole), default=enums.ProjectRole.CONTRIBUTOR)

    project: Mapped[Project] = relationship(back_populates="members")


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[enums.ArticleStatus] = mapped_column(SAEnum(enums.ArticleStatus), default=enums.ArticleStatus.IDEA)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    target_journal: Mapped[str | None] = mapped_column(String(200), nullable=True)
    document_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    members: Mapped[list[ArticleMember]] = relationship(
        back_populates="article", cascade="all, delete-orphan"
    )


class ArticleMember(Base):
    __tablename__ = "article_members"
    __table_args__ = (UniqueConstraint("article_id", "user_id", name="uq_art_member"),)

    id: Mapped[str] = PK()
    article_id: Mapped[str] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[enums.ArticleRole] = mapped_column(SAEnum(enums.ArticleRole), default=enums.ArticleRole.CO_AUTHOR)

    article: Mapped[Article] = relationship(back_populates="members")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    article_id: Mapped[str | None] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[enums.TaskScope] = mapped_column(SAEnum(enums.TaskScope), nullable=False)
    visibility: Mapped[enums.TaskVisibility] = mapped_column(SAEnum(enums.TaskVisibility), nullable=False)
    status: Mapped[enums.TaskStatus] = mapped_column(SAEnum(enums.TaskStatus), default=enums.TaskStatus.TODO)
    type: Mapped[enums.TaskType] = mapped_column(SAEnum(enums.TaskType), default=enums.TaskType.OTHER)
    priority: Mapped[enums.TaskPriority] = mapped_column(SAEnum(enums.TaskPriority), default=enums.TaskPriority.MEDIUM)
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    article_id: Mapped[str | None] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), nullable=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[enums.TaskVisibility] = mapped_column(
        SAEnum(enums.TaskVisibility), default=enums.TaskVisibility.WORKSPACE
    )
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (
        UniqueConstraint("source_event_id", "user_id", "reward_type", name="uq_reward_event"),
    )

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    source_event_id: Mapped[str] = mapped_column(ForeignKey("domain_events.id", ondelete="CASCADE"))
    xp_amount: Mapped[int] = mapped_column(Integer, default=0)
    reward_type: Mapped[enums.RewardType] = mapped_column(SAEnum(enums.RewardType), default=enums.RewardType.XP)
    privacy_level: Mapped[enums.PrivacyLevel] = mapped_column(
        SAEnum(enums.PrivacyLevel), default=enums.PrivacyLevel.WORKSPACE
    )
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
    visibility: Mapped[enums.TaskVisibility] = mapped_column(
        SAEnum(enums.TaskVisibility), default=enums.TaskVisibility.WORKSPACE
    )
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
    privacy_level: Mapped[enums.PrivacyLevel] = mapped_column(
        SAEnum(enums.PrivacyLevel), default=enums.PrivacyLevel.WORKSPACE
    )
    payload: Mapped[dict] = mapped_column(JsonType, default=dict)
    status: Mapped[enums.EventStatus] = mapped_column(SAEnum(enums.EventStatus), default=enums.EventStatus.PENDING)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = TS()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WallPost(Base):
    """Сообщение на «Стене» рабочего пространства (лёгкая лента для участников)."""
    __tablename__ = "wall_posts"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = TS()


class WallReaction(Base):
    __tablename__ = "wall_reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id", "emoji", name="uq_wall_reaction"),)

    id: Mapped[str] = PK()
    post_id: Mapped[str] = mapped_column(ForeignKey("wall_posts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    emoji: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = TS()


class WallPresence(Base):
    __tablename__ = "wall_presence"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_wall_presence"),)

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
