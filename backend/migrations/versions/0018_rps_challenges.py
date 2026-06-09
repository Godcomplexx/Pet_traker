"""rock paper scissors challenges

Revision ID: 0018_rps_challenges
Revises: 0017_pet_lifecycle
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018_rps_challenges"
down_revision: Union[str, None] = "0017_pet_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "rps_challenges"):
        return
    op.create_table(
        "rps_challenges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("challenger_id", sa.String(length=36), nullable=False),
        sa.Column("opponent_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("challenger_choice", sa.String(length=12), nullable=True),
        sa.Column("opponent_choice", sa.String(length=12), nullable=True),
        sa.Column("winner_id", sa.String(length=36), nullable=True),
        sa.Column("reward_awarded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenger_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opponent_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_rps_challenges_workspace_id", "rps_challenges", ["workspace_id"])
    op.create_index("ix_rps_challenges_challenger_id", "rps_challenges", ["challenger_id"])
    op.create_index("ix_rps_challenges_opponent_id", "rps_challenges", ["opponent_id"])
    op.create_index("ix_rps_challenges_status", "rps_challenges", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "rps_challenges"):
        return
    op.drop_index("ix_rps_challenges_status", table_name="rps_challenges")
    op.drop_index("ix_rps_challenges_opponent_id", table_name="rps_challenges")
    op.drop_index("ix_rps_challenges_challenger_id", table_name="rps_challenges")
    op.drop_index("ix_rps_challenges_workspace_id", table_name="rps_challenges")
    op.drop_table("rps_challenges")
