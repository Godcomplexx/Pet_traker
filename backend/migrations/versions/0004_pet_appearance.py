"""pet appearance: body_color, accent_color, customized + species default

Revision ID: 0004_pet_look
Revises: 0003_email_verif
Create Date: 2026-05-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_pet_look"
down_revision: Union[str, None] = "0003_email_verif"
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

    if not _column_exists(bind, "pets", "body_color"):
        op.add_column("pets", sa.Column("body_color", sa.String(length=9), nullable=False, server_default="#d99a52"))

    if not _column_exists(bind, "pets", "accent_color"):
        op.add_column("pets", sa.Column("accent_color", sa.String(length=9), nullable=False, server_default="#7a3a22"))

    if not _column_exists(bind, "pets", "customized"):
        op.add_column("pets", sa.Column("customized", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("pets", "customized")
    op.drop_column("pets", "accent_color")
    op.drop_column("pets", "body_color")
