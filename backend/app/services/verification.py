"""Генерация и проверка кодов подтверждения email."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import EmailVerification
from app.services.email import send_verification_code

MAX_ATTEMPTS = 5


def _gen_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def issue_code(db: AsyncSession, user_id: str, email: str) -> tuple[str, bool]:
    """Создать новый код, погасить старые, отправить письмо.

    Возвращает (код, отправлено_ли_реально_по_smtp).
    """
    # Гасим прежние неиспользованные коды этого пользователя.
    old = await db.scalars(
        select(EmailVerification).where(
            EmailVerification.user_id == user_id,
            EmailVerification.consumed_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for ev in old.all():
        ev.consumed_at = now

    code = _gen_code()
    db.add(
        EmailVerification(
            user_id=user_id,
            code=code,
            expires_at=now + timedelta(minutes=settings.verification_code_ttl_minutes),
        )
    )
    await db.flush()
    sent = send_verification_code(email, code)
    return code, sent


async def verify_code(db: AsyncSession, user_id: str, code: str) -> tuple[bool, str]:
    """Проверить код. Возвращает (успех, сообщение_об_ошибке)."""
    ev = await db.scalar(
        select(EmailVerification)
        .where(
            EmailVerification.user_id == user_id,
            EmailVerification.consumed_at.is_(None),
        )
        .order_by(EmailVerification.created_at.desc())
    )
    if ev is None:
        return False, "Код не найден. Запросите новый."

    now = datetime.now(timezone.utc)
    expires = ev.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        return False, "Код истёк. Запросите новый."

    if ev.attempts >= MAX_ATTEMPTS:
        return False, "Слишком много попыток. Запросите новый код."

    if ev.code != code:
        ev.attempts += 1
        await db.flush()
        return False, "Неверный код подтверждения."

    ev.consumed_at = now
    await db.flush()
    return True, ""
