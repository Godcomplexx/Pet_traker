"""board position: projects/articles/tasks.position для канбана

Revision ID: 0015_board_position
Revises: 0014_zip_scores
Create Date: 2026-06-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_board_position"
down_revision: Union[str, None] = "0014_zip_scores"
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
    for table in ("projects", "articles", "tasks"):
        if not _column_exists(bind, table, "position"):
            op.add_column(
                table,
                sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            )
            # начальный порядок = по дате создания (старые выше)
            op.execute(
                f"""
                UPDATE {table} AS t SET position = sub.rn
                FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY {'workspace_id' if table != 'tasks' else 'COALESCE(project_id, article_id, workspace_id)'} , status
                        ORDER BY created_at
                    ) AS rn
                    FROM {table}
                ) AS sub
                WHERE t.id = sub.id
                """
            )


def downgrade() -> None:
    for table in ("tasks", "articles", "projects"):
        op.drop_column(table, "position")
