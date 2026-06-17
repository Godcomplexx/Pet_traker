from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _join_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


JsonType = JSONB().with_variant(sa.JSON(), "sqlite")

PK = lambda: mapped_column(String(36), primary_key=True, default=_uuid)  # noqa: E731
TS = lambda: mapped_column(DateTime(timezone=True), default=_now)  # noqa: E731
