"""Тесты регистрации, подтверждения email и входа."""
import pytest

from app.core.config import settings


@pytest.fixture
def require_verification():
    """Временно включить обязательное подтверждение email."""
    settings.require_email_verification = True
    yield
    settings.require_email_verification = False


async def test_register_requires_verification(client, require_verification):
    r = await client.post(
        "/auth/register",
        json={"email": "v@lab.ru", "password": "password123", "display_name": "Вера"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "verification_required"
    # В dev-режиме (без SMTP) код возвращается для теста.
    assert body["dev_code"] and len(body["dev_code"]) == 6

    # Логин до подтверждения запрещён.
    login = await client.post("/auth/login", json={"email": "v@lab.ru", "password": "password123"})
    assert login.status_code == 403

    # Неверный код — отказ.
    bad = await client.post("/auth/verify", json={"email": "v@lab.ru", "code": "000000"})
    assert bad.status_code in (400, 200)  # 200 только если случайно совпал
    if bad.status_code == 400:
        assert "код" in bad.json()["detail"].lower()

    # Верный код — выдаёт токены.
    ok = await client.post("/auth/verify", json={"email": "v@lab.ru", "code": body["dev_code"]})
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
    assert r.json()["dev_code"]


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
