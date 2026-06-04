"""daily check-in and sudoku rewards

Revision ID: 0012_daily_sudoku_rewards
Revises: 0011_task_people
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_daily_sudoku_rewards"
down_revision: Union[str, None] = "0012_daily_games"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(bind, table: str, column: str) -> bool:
    if bind.dialect.name == "postgresql":
        return bind.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c"
            ),
            {"t": table, "c": column},
        ).fetchone() is not None
    rows = bind.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in rows)


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "pets", "daily_claimed_on"):
        op.add_column("pets", sa.Column("daily_claimed_on", sa.Date(), nullable=True))
    if not _column_exists(bind, "pets", "sudoku_completed_on"):
        op.add_column("pets", sa.Column("sudoku_completed_on", sa.Date(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _column_exists(bind, "pets", "sudoku_completed_on"):
        op.drop_column("pets", "sudoku_completed_on")
    if _column_exists(bind, "pets", "daily_claimed_on"):
        op.drop_column("pets", "daily_claimed_on")
