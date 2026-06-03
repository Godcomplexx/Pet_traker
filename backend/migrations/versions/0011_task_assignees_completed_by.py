"""task: multiple assignees + completed_by

Revision ID: 0011_task_people
Revises: 0010_pet_food_inventory
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_task_people"
down_revision: Union[str, None] = "0010_pet_food_inventory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(bind, table: str, column: str) -> bool:
    return bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "tasks", "assignees"):
        op.add_column(
            "tasks",
            sa.Column("assignees", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        )
    if not _column_exists(bind, "tasks", "completed_by"):
        op.add_column("tasks", sa.Column("completed_by", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "completed_by")
    op.drop_column("tasks", "assignees")
