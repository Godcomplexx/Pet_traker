import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import Base, engine
from app.api.routers import (
    articles,
    auth,
    comments,
    feed,
    games,
    minesweeper,
    pets,
    projects,
    shop,
    tasks,
    wall,
    workspaces,
)

# Import models so they are registered on Base.metadata before create_all.
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev convenience: ensure schema exists. Production uses Alembic migrations.
    if settings.env != "production":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="LabMate API",
    description="Lab Project Tracker with Pet Gamification",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Поля → человеко-читаемые имена для сообщений об ошибках валидации.
_FIELD_LABELS = {
    "email": "Email",
    "password": "Пароль",
    "display_name": "Имя",
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Возвращаем первое понятное сообщение + словарь ошибок по полям."""
    field_errors: dict[str, str] = {}
    for err in exc.errors():
        loc = [p for p in err.get("loc", []) if p != "body"]
        field = loc[-1] if loc else "general"
        msg = err.get("msg", "Некорректное значение")
        msg = msg.replace("Value error, ", "")
        if err.get("type") == "value_error.email" or "valid email" in msg.lower():
            msg = "Введите корректный email"
        field_errors.setdefault(str(field), msg)

    first = next(iter(field_errors.values()), "Проверьте введённые данные")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": first, "errors": field_errors},
    )


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


for r in (auth, pets, shop, workspaces, projects, articles, tasks, comments, feed, wall, games, minesweeper):
    app.include_router(r.router, prefix="/api")


# ── Раздача фронтенда из того же сервиса (единый origin, без CORS-проблем) ──
# Путь к статике задаётся FRONTEND_DIR (в Docker — /app/frontend). Монтируется
# последним, чтобы не перехватывать /api и /health. html=True → отдаёт index.html.
_frontend_dir = os.environ.get("FRONTEND_DIR", "")
if _frontend_dir and os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
