"""pet gamification settings

Revision ID: 0023_pet_gamification_settings
Revises: 0022_audit_logs
Create Date: 2026-06-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_pet_gamification_settings"
down_revision: Union[str, None] = "0022_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(bind, table: str, column: str) -> bool:
    return column in {col["name"] for col in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "pets", "gamification_muted"):
        op.add_column(
            "pets",
            sa.Column(
                "gamification_muted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _column_exists(bind, "pets", "gamification_muted"):
        op.drop_column("pets", "gamification_muted")
