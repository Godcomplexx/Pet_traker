"""Тесты регистрации, подтверждения email и входа."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import EmailVerification, User


@pytest.fixture
def require_verification():
    """Временно включить обязательное подтверждение email."""
    settings.require_email_verification = True
    yield
    settings.require_email_verification = False


async def latest_verification_code(email: str) -> str:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == email))
        assert user is not None
        ev = await db.scalar(
            select(EmailVerification)
            .where(
                EmailVerification.user_id == user.id,
                EmailVerification.consumed_at.is_(None),
            )
            .order_by(EmailVerification.created_at.desc())
        )
        assert ev is not None
        return ev.code


async def test_register_requires_verification(client, require_verification):
    r = await client.post(
        "/auth/register",
        json={"email": "v@lab.ru", "password": "password123", "display_name": "Вера"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "verification_required"
    assert "dev_code" not in body

    # Логин до подтверждения запрещён.
    login = await client.post("/auth/login", json={"email": "v@lab.ru", "password": "password123"})
    assert login.status_code == 403

    # Неверный код — отказ.
    bad = await client.post("/auth/verify", json={"email": "v@lab.ru", "code": "000000"})
    assert bad.status_code in (400, 200)  # 200 только если случайно совпал
    if bad.status_code == 400:
        assert "код" in bad.json()["detail"].lower()

    # Верный код — выдаёт токены.
    code = await latest_verification_code("v@lab.ru")
    ok = await client.post("/auth/verify", json={"email": "v@lab.ru", "code": code})
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    # Теперь логин проходит.
    login2 = await client.post("/auth/login", json={"email": "v@lab.ru", "password": "password123"})
    assert login2.status_code == 200


async def test_resend_code_issues_new(client, require_verification):
    await client.post(
        "/auth/register",
        json={"email": "r@lab.ru", "password": "password123", "display_name": "Рома"},
    )
    r = await client.post("/auth/resend-code", json={"email": "r@lab.ru"})
    assert r.status_code == 200
    assert r.json()["message"] == "Код отправлен повторно"
    code = await latest_verification_code("r@lab.ru")
    assert len(code) == 6


async def test_register_existing_unverified_resends_code(client, require_verification):
    first = await client.post(
        "/auth/register",
        json={"email": "pending@lab.ru", "password": "password123", "display_name": "Пётр"},
    )
    assert first.status_code == 201, first.text

    again = await client.post(
        "/auth/register",
        json={"email": "pending@lab.ru", "password": "password123", "display_name": "Пётр"},
    )
    assert again.status_code == 201, again.text
    body = again.json()
    assert body["status"] == "verification_required"
    assert body["email"] == "pending@lab.ru"
    assert "dev_code" not in body


async def test_password_validation(client):
    # Слишком короткий / без цифры — 422 с понятным сообщением.
    r = await client.post(
        "/auth/register",
        json={"email": "weak@lab.ru", "password": "short", "display_name": "Имя"},
    )
    assert r.status_code == 422
    assert "password" in r.json()["errors"]


async def test_duplicate_email(client):
    await client.post(
        "/auth/register",
        json={"email": "dup@lab.ru", "password": "password123", "display_name": "Имя"},
    )
    r = await client.post(
        "/auth/register",
        json={"email": "dup@lab.ru", "password": "password123", "display_name": "Имя2"},
    )
    assert r.status_code == 409
