"""minesweeper scores leaderboard

Revision ID: 0016_minesweeper_scores
Revises: 0015_board_position
Create Date: 2026-06-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016_minesweeper_scores"
down_revision: Union[str, None] = "0015_board_position"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "minesweeper_scores"):
        op.create_table(
            "minesweeper_scores",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("puzzle_date", sa.String(length=10), nullable=False),
            sa.Column("seconds", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "puzzle_date", name="uq_minesweeper_score_user_day"),
        )
        op.create_index("ix_minesweeper_scores_user_id", "minesweeper_scores", ["user_id"])
        op.create_index("ix_minesweeper_scores_puzzle_date", "minesweeper_scores", ["puzzle_date"])


def downgrade() -> None:
    op.drop_index("ix_minesweeper_scores_puzzle_date", table_name="minesweeper_scores")
    op.drop_index("ix_minesweeper_scores_user_id", table_name="minesweeper_scores")
    op.drop_table("minesweeper_scores")
