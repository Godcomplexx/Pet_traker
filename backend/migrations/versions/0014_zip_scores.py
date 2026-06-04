"""zip scores leaderboard

Revision ID: 0014_zip_scores
Revises: 0013_sudoku_scores
Create Date: 2026-06-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_zip_scores"
down_revision: Union[str, None] = "0013_sudoku_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "zip_scores"):
        op.create_table(
            "zip_scores",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("puzzle_date", sa.String(length=10), nullable=False),
            sa.Column("seconds", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("user_id", "puzzle_date", name="uq_zip_score_user_day"),
        )
        op.create_index("ix_zip_scores_user_id", "zip_scores", ["user_id"])
        op.create_index("ix_zip_scores_puzzle_date", "zip_scores", ["puzzle_date"])


def downgrade() -> None:
    op.drop_index("ix_zip_scores_puzzle_date", table_name="zip_scores")
    op.drop_index("ix_zip_scores_user_id", table_name="zip_scores")
    op.drop_table("zip_scores")
