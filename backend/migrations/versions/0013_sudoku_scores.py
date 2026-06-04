"""sudoku scores leaderboard

Revision ID: 0013_sudoku_scores
Revises: 0012_daily_sudoku_rewards
Create Date: 2026-06-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_sudoku_scores"
down_revision: Union[str, None] = "0012_daily_sudoku_rewards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "sudoku_scores"):
        op.create_table(
            "sudoku_scores",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("puzzle_date", sa.String(length=10), nullable=False),
            sa.Column("seconds", sa.Integer(), nullable=False),
            sa.Column("hints_used", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "puzzle_date", name="uq_sudoku_score_user_day"),
        )
        op.create_index("ix_sudoku_scores_user_id", "sudoku_scores", ["user_id"])
        op.create_index("ix_sudoku_scores_puzzle_date", "sudoku_scores", ["puzzle_date"])


def downgrade() -> None:
    op.drop_index("ix_sudoku_scores_puzzle_date", table_name="sudoku_scores")
    op.drop_index("ix_sudoku_scores_user_id", table_name="sudoku_scores")
    op.drop_table("sudoku_scores")
