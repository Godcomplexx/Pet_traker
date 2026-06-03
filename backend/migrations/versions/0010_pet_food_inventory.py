"""add pet food inventory

Revision ID: 0010_pet_food_inventory
Revises: 0009_wall_presence
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_pet_food_inventory"
down_revision: Union[str, None] = "0009_wall_presence"
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
    if _column_exists(bind, "pets", "food_inventory"):
        return
    if bind.dialect.name == "postgresql":
        op.add_column(
            "pets",
            sa.Column(
                "food_inventory",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )
        return
    op.add_column("pets", sa.Column("food_inventory", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    op.drop_column("pets", "food_inventory")
