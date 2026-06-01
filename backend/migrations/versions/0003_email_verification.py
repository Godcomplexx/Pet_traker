"""email verification: users.email_verified + email_verifications table

Revision ID: 0003_email_verif
Revises: 0002_join_code
Create Date: 2026-05-31
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_email_verif"
down_revision: Union[str, None] = "0002_join_code"
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

    if not _column_exists(bind, "users", "email_verified"):
        op.add_column(
            "users",
            sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.execute("UPDATE users SET email_verified = true")

    if not _table_exists(bind, "email_verifications"):
        op.create_table(
            "email_verifications",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("code", sa.String(length=6), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )

    if not _index_exists(bind, "ix_email_verifications_user_id"):
        op.create_index("ix_email_verifications_user_id", "email_verifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_email_verifications_user_id", table_name="email_verifications")
    op.drop_table("email_verifications")
    op.drop_column("users", "email_verified")
