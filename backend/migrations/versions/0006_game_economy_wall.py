"""game economy (pet coins + inventory) and workspace wall

Revision ID: 0006_game_wall
Revises: 0005_pet_clock
Create Date: 2026-06-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_game_wall"
down_revision: Union[str, None] = "0005_pet_clock"
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


def _table_exists(bind, table: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name=:t"),
        {"t": table},
    ).fetchone() is not None


def _index_exists(bind, index: str) -> bool:
    return bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname=:i"),
        {"i": index},
    ).fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # ── pet economy ──
    if not _column_exists(bind, "pets", "coins"):
        op.add_column("pets", sa.Column("coins", sa.Integer(), nullable=False, server_default="0"))
    if not _column_exists(bind, "pets", "inventory"):
        # JSONB на Postgres; дефолт — пустой массив.
        op.add_column(
            "pets",
            sa.Column(
                "inventory", postgresql.JSONB(),
                nullable=False, server_default=sa.text("'[]'::jsonb"),
            ),
        )
    if not _column_exists(bind, "pets", "equipped"):
        op.add_column(
            "pets",
            sa.Column(
                "equipped", postgresql.JSONB(),
                nullable=False, server_default=sa.text("'{}'::jsonb"),
            ),
        )

    # ── workspace wall ──
    if not _table_exists(bind, "wall_posts"):
        op.create_table(
            "wall_posts",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("author_id", sa.String(length=36), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        )
    if not _index_exists(bind, "ix_wall_posts_workspace_id"):
        op.create_index("ix_wall_posts_workspace_id", "wall_posts", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_wall_posts_workspace_id", table_name="wall_posts")
    op.drop_table("wall_posts")
    op.drop_column("pets", "equipped")
    op.drop_column("pets", "inventory")
    op.drop_column("pets", "coins")
