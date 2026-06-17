from __future__ import annotations

import enum
from datetime import date
from functools import singledispatch
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


@singledispatch
def audit_value(value: Any) -> Any:
    return value


@audit_value.register
def _(value: enum.Enum) -> Any:
    return value.value


@audit_value.register
def _(value: date) -> str:
    return value.isoformat()


@audit_value.register
def _(value: list) -> list:
    return [audit_value(item) for item in value]


@audit_value.register
def _(value: tuple) -> list:
    return [audit_value(item) for item in value]


@audit_value.register
def _(value: set) -> list:
    return [audit_value(item) for item in value]


@audit_value.register
def _(value: dict) -> dict:
    return {str(key): audit_value(item) for key, item in value.items()}


def snapshot_fields(entity: object, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: audit_value(getattr(entity, field)) for field in fields}


def diff_snapshots(
    before: dict[str, Any], after: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    changed = [field for field in before if before.get(field) != after.get(field)]
    return (
        {field: before[field] for field in changed},
        {field: after[field] for field in changed},
    )


def record_audit(
    db: AsyncSession,
    *,
    workspace_id: str | None,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    target_user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    if workspace_id is None:
        return
    clean_before = audit_value(before or {})
    clean_after = audit_value(after or {})
    db.add(
        AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            target_user_id=target_user_id,
            before=clean_before,
            after=clean_after,
            details=audit_value(details or {}),
        )
    )
