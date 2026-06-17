"""task checklist items

Revision ID: 0019_task_checklist_items
Revises: 0018_rps_challenges
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019_task_checklist_items"
down_revision: Union[str, None] = "0018_rps_challenges"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "task_checklist_items"):
        return
    op.create_table(
        "task_checklist_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False, server_default="CHECK"),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_task_checklist_items_task_id", "task_checklist_items", ["task_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "task_checklist_items"):
        return
    op.drop_index("ix_task_checklist_items_task_id", table_name="task_checklist_items")
    op.drop_table("task_checklist_items")
