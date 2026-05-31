"""pet tamagotchi: stats_updated_at

Revision ID: 0005_pet_clock
Revises: 0004_pet_look
Create Date: 2026-05-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_pet_clock"
down_revision: Union[str, None] = "0004_pet_look"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pets",
        sa.Column(
            "stats_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_column("pets", "stats_updated_at")
