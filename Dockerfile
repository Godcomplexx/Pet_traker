# Единый образ для деплоя на Render (и веб-сервис, и воркер).
# Веб-сервис раздаёт API + статику фронта из одного origin.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIR=/app/frontend

WORKDIR /app

# Зависимости и код бэкенда.
COPY backend/ /app/
RUN pip install --upgrade pip && pip install .

# Статика фронтенда — раздаётся FastAPI через StaticFiles (FRONTEND_DIR).
COPY frontend/ /app/frontend/

EXPOSE 8000

# По умолчанию — веб-сервис: миграции + API. Render передаёт $PORT.
# Воркер переопределяет команду в render.yaml.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
