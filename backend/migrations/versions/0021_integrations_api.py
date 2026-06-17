"""integrations api

Revision ID: 0021_integrations_api
Revises: 0020_attachments
Create Date: 2026-06-16
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021_integrations_api"
down_revision: Union[str, None] = "0020_attachments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table: str) -> bool:
    return table in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "api_tokens"):
        op.create_table(
            "api_tokens",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("token_prefix", sa.String(length=16), nullable=False),
            sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])
        op.create_index("ix_api_tokens_token_hash", "api_tokens", ["token_hash"], unique=True)

    if not _table_exists(bind, "webhook_subscriptions"):
        op.create_table(
            "webhook_subscriptions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=False),
            sa.Column("secret_hash", sa.String(length=64), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("events", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_webhook_subscriptions_workspace_id", "webhook_subscriptions", ["workspace_id"])

    if not _table_exists(bind, "webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("subscription_id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("event_id", sa.String(length=36), nullable=True),
            sa.Column("event_type", sa.String(length=80), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(length=24), nullable=False, server_default="queued"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["event_id"], ["domain_events.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_webhook_deliveries_subscription_id", "webhook_deliveries", ["subscription_id"])
        op.create_index("ix_webhook_deliveries_workspace_id", "webhook_deliveries", ["workspace_id"])
        op.create_index("ix_webhook_deliveries_status", "webhook_deliveries", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "webhook_deliveries"):
        op.drop_index("ix_webhook_deliveries_status", table_name="webhook_deliveries")
        op.drop_index("ix_webhook_deliveries_workspace_id", table_name="webhook_deliveries")
        op.drop_index("ix_webhook_deliveries_subscription_id", table_name="webhook_deliveries")
        op.drop_table("webhook_deliveries")
    if _table_exists(bind, "webhook_subscriptions"):
        op.drop_index("ix_webhook_subscriptions_workspace_id", table_name="webhook_subscriptions")
        op.drop_table("webhook_subscriptions")
    if _table_exists(bind, "api_tokens"):
        op.drop_index("ix_api_tokens_token_hash", table_name="api_tokens")
        op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
        op.drop_table("api_tokens")
