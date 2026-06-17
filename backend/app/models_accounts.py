from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models_common import JsonType, PK, TS, _now


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = PK()
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = TS()


class Pet(Base):
    __tablename__ = "pets"

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(80), default="Питомец")
    species: Mapped[str] = mapped_column(String(40), default="capybara")
    body_color: Mapped[str] = mapped_column(String(9), default="#d99a52")
    accent_color: Mapped[str] = mapped_column(String(9), default="#7a3a22")
    customized: Mapped[bool] = mapped_column(Boolean, default=False)
    gamification_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    mood: Mapped[int] = mapped_column(Integer, default=80)
    hunger: Mapped[int] = mapped_column(Integer, default=70)
    energy: Mapped[int] = mapped_column(Integer, default=80)
    is_dead: Mapped[bool] = mapped_column(Boolean, default=False)
    died_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    neglect_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    daily_claimed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    sudoku_completed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    inventory: Mapped[list] = mapped_column(JsonType, default=list)
    food_inventory: Mapped[dict] = mapped_column(JsonType, default=dict)
    equipped: Mapped[dict] = mapped_column(JsonType, default=dict)
    stats_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="pet")
