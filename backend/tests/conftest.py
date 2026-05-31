import os
import pathlib

# Configure the environment BEFORE importing any app module so the engine and
# settings bind to a throwaway SQLite database with inline event processing.
_DB_FILE = pathlib.Path(__file__).parent / "test_petpro.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DB_FILE.as_posix()}"
os.environ["EVENT_MODE"] = "inline"
os.environ["JWT_SECRET"] = "test_secret"
os.environ["ENV"] = "test"
# Большинство тестов используют прямой register→токены; флоу верификации
# проверяется отдельно в test_auth.py с переопределением настройки.
os.environ["REQUIRE_EMAIL_VERIFICATION"] = "false"

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    # Fresh schema per test (drop+create reuses pooled connections — Windows-safe).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api") as ac:
        yield ac

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def register(client: AsyncClient, email: str, name: str = "User") -> dict:
    """Регистрирует пользователя и возвращает пару токенов (через login).

    С REQUIRE_EMAIL_VERIFICATION=false аккаунт сразу активен, поэтому login
    проходит без подтверждения.
    """
    resp = await client.post(
        "/auth/register", json={"email": email, "password": "password123", "display_name": name}
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200, login.text
    return login.json()


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
