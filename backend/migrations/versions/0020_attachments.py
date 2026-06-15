"""attachments

Revision ID: 0020_attachments
Revises: 0019_task_checklist_items
Create Date: 2026-06-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_attachments"
down_revision: Union[str, None] = "0019_task_checklist_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "attachments"):
        return
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("article_id", sa.String(length=36), nullable=True),
        sa.Column("uploaded_by", sa.String(length=36), nullable=True),
        sa.Column("original_name", sa.String(length=300), nullable=False),
        sa.Column("stored_name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_attachments_workspace_id", "attachments", ["workspace_id"])
    op.create_index("ix_attachments_task_id", "attachments", ["task_id"])
    op.create_index("ix_attachments_project_id", "attachments", ["project_id"])
    op.create_index("ix_attachments_article_id", "attachments", ["article_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "attachments"):
        return
    op.drop_index("ix_attachments_article_id", table_name="attachments")
    op.drop_index("ix_attachments_project_id", table_name="attachments")
    op.drop_index("ix_attachments_task_id", table_name="attachments")
    op.drop_index("ix_attachments_workspace_id", table_name="attachments")
    op.drop_table("attachments")
