"""add wall presence

Revision ID: 0009_wall_presence
Revises: 0008_wall_images_reactions
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_wall_presence"
down_revision: Union[str, None] = "0008_wall_images_reactions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    if bind.dialect.name == "postgresql":
        return bind.execute(
            sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
            {"t": table},
        ).fetchone() is not None
    return bind.execute(
        sa.text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "wall_presence"):
        return
    op.create_table(
        "wall_presence",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_wall_presence"),
    )
    op.create_index("ix_wall_presence_workspace_id", "wall_presence", ["workspace_id"])
    op.create_index("ix_wall_presence_user_id", "wall_presence", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_wall_presence_user_id", table_name="wall_presence")
    op.drop_index("ix_wall_presence_workspace_id", table_name="wall_presence")
    op.drop_table("wall_presence")
