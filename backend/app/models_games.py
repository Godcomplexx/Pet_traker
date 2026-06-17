from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models_common import PK, TS, _now


class WallPost(Base):
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


class RpsChallenge(Base):
    __tablename__ = "rps_challenges"

    id: Mapped[str] = PK()
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    challenger_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    opponent_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    challenger_choice: Mapped[str | None] = mapped_column(String(12), nullable=True)
    opponent_choice: Mapped[str | None] = mapped_column(String(12), nullable=True)
    winner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reward_awarded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = TS()
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DailyGameCompletion(Base):
    __tablename__ = "daily_game_completions"
    __table_args__ = (UniqueConstraint("user_id", "game", "day", name="uq_daily_game"),)

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    game: Mapped[str] = mapped_column(String(40), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = TS()


class SudokuScore(Base):
    __tablename__ = "sudoku_scores"
    __table_args__ = (UniqueConstraint("user_id", "puzzle_date", name="uq_sudoku_score_user_day"),)

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    puzzle_date: Mapped[str] = mapped_column(String(10), index=True)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    hints_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ZipScore(Base):
    __tablename__ = "zip_scores"
    __table_args__ = (UniqueConstraint("user_id", "puzzle_date", name="uq_zip_score_user_day"),)

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    puzzle_date: Mapped[str] = mapped_column(String(10), index=True)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class MinesweeperScore(Base):
    __tablename__ = "minesweeper_scores"
    __table_args__ = (UniqueConstraint("user_id", "puzzle_date", name="uq_minesweeper_score_user_day"),)

    id: Mapped[str] = PK()
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    puzzle_date: Mapped[str] = mapped_column(String(10), index=True)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = TS()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
