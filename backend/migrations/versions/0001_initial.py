"""initial baseline schema

Creates all tables from the current ORM metadata. Subsequent changes should use
`alembic revision --autogenerate`. Using the metadata here keeps dialect-specific
types correct (e.g. JSONB on PostgreSQL) without hand-transcribing 14 tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-30
"""
from typing import Sequence, Union
from importlib import import_module

from alembic import op

from app.core.database import Base

import_module("app.models")

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
