"""pet lifecycle death state

Revision ID: 0017_pet_lifecycle
Revises: 0016_minesweeper_scores
Create Date: 2026-06-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017_pet_lifecycle"
down_revision: Union[str, None] = "0016_minesweeper_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(bind, table: str, column: str) -> bool:
    return column in {col["name"] for col in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "pets", "is_dead"):
        op.add_column(
            "pets",
            sa.Column("is_dead", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _column_exists(bind, "pets", "died_at"):
        op.add_column("pets", sa.Column("died_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(bind, "pets", "neglect_started_at"):
        op.add_column(
            "pets",
            sa.Column("neglect_started_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _column_exists(bind, "pets", "neglect_started_at"):
        op.drop_column("pets", "neglect_started_at")
    if _column_exists(bind, "pets", "died_at"):
        op.drop_column("pets", "died_at")
    if _column_exists(bind, "pets", "is_dead"):
        op.drop_column("pets", "is_dead")
