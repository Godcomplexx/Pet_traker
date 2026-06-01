from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "development"

    database_url: str = "postgresql+asyncpg://petpro:petpro_dev_password@localhost:5432/petpro"
    redis_url: str = "redis://localhost:6379/0"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, v: str) -> str:
        """Managed-провайдеры (Render, Heroku) дают URL вида postgres://… —
        приводим к async-драйверу SQLAlchemy postgresql+asyncpg://…"""
        if not isinstance(v, str):
            return v
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    jwt_secret: str = "change_me_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = (
        "http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500,"
        "http://localhost:8080,http://127.0.0.1:8080"
    )

    # How domain events are processed after a mutation:
    #   "inline"  — process in-process (dev default; no separate worker needed)
    #   "taskiq"  — enqueue to Redis/Taskiq worker (production / scale)
    event_mode: str = "inline"

    # ── Email / подтверждение регистрации ──
    # Требовать подтверждение email кодом перед входом.
    require_email_verification: bool = True
    # Время жизни кода подтверждения (минуты).
    verification_code_ttl_minutes: int = 15
    # SMTP. Если smtp_host пуст — письма не отправляются реально,
    # код пишется в логи (dev-режим). Заполните для реальной отправки.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    mail_from: str = "PetPro <noreply@petpro.app>"

    @property
    def smtp_enabled(self) -> bool:
        return bool(self.smtp_host and self.smtp_user)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
