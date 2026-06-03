"""daily game completions (ежедневные мини-игры: судоку и др.)

Revision ID: 0012_daily_games
Revises: 0011_task_people
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_daily_games"
down_revision: Union[str, None] = "0011_task_people"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "daily_game_completions"):
        op.create_table(
            "daily_game_completions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("game", sa.String(length=40), nullable=False),
            sa.Column("day", sa.Date(), nullable=False),
            sa.Column("coins_awarded", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "game", "day", name="uq_daily_game"),
        )
        op.create_index("ix_daily_game_completions_user_id", "daily_game_completions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_daily_game_completions_user_id", table_name="daily_game_completions")
    op.drop_table("daily_game_completions")
