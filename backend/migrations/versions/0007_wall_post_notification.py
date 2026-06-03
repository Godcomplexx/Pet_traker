"""add wall post notification type

Revision ID: 0007_wall_post_notification
Revises: 0006_game_wall
Create Date: 2026-06-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0007_wall_post_notification"
down_revision: Union[str, None] = "0006_game_wall"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'WALL_POST'")


def downgrade() -> None:
    # PostgreSQL cannot drop enum values without recreating the type.
    pass
