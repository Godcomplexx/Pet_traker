"""add workspaces.join_code

Revision ID: 0002_join_code
Revises: 0001_initial
Create Date: 2026-05-31
"""
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_join_code"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(8))


def _column_exists(bind, table: str, column: str) -> bool:
    row = bind.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def _index_exists(bind, index: str) -> bool:
    row = bind.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname=:i"),
        {"i": index},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    bind = op.get_bind()

    # 0001_initial already creates the column via create_all — skip if present.
    if not _column_exists(bind, "workspaces", "join_code"):
        op.add_column("workspaces", sa.Column("join_code", sa.String(length=12), nullable=True))

        rows = bind.execute(sa.text("SELECT id FROM workspaces")).fetchall()
        used: set[str] = set()
        for (ws_id,) in rows:
            code = _code()
            while code in used:
                code = _code()
            used.add(code)
            bind.execute(
                sa.text("UPDATE workspaces SET join_code = :c WHERE id = :i"),
                {"c": code, "i": ws_id},
            )

        op.alter_column("workspaces", "join_code", nullable=False)

    if not _index_exists(bind, "ix_workspaces_join_code"):
        op.create_index("ix_workspaces_join_code", "workspaces", ["join_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workspaces_join_code", table_name="workspaces")
    op.drop_column("workspaces", "join_code")
