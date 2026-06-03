"""add wall images and reactions

Revision ID: 0008_wall_images_reactions
Revises: 0007_wall_post_notification
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_wall_images_reactions"
down_revision: Union[str, None] = "0007_wall_post_notification"
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
    return column in {row[1] for row in bind.execute(sa.text(f"PRAGMA table_info({table})"))}


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
    if not _column_exists(bind, "wall_posts", "image_data"):
        op.add_column("wall_posts", sa.Column("image_data", sa.Text(), nullable=True))
    if not _table_exists(bind, "wall_reactions"):
        op.create_table(
            "wall_reactions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("post_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("emoji", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["post_id"], ["wall_posts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("post_id", "user_id", "emoji", name="uq_wall_reaction"),
        )
        op.create_index("ix_wall_reactions_post_id", "wall_reactions", ["post_id"])
        op.create_index("ix_wall_reactions_user_id", "wall_reactions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_wall_reactions_user_id", table_name="wall_reactions")
    op.drop_index("ix_wall_reactions_post_id", table_name="wall_reactions")
    op.drop_table("wall_reactions")
    op.drop_column("wall_posts", "image_data")
