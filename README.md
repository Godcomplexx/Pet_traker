# LabMate

<p align="center">
  <a href="#russian"><strong>Русский</strong></a>
  &nbsp;|&nbsp;
  <a href="#english"><strong>English</strong></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white">
</p>

<p align="center">
  <strong>Lab project tracker with task boards, research workflows, team activity, and pet gamification.</strong>
</p>

<p align="center">
  <a href="#быстрый-старт-через-docker">Быстрый старт</a>
  &nbsp;·&nbsp;
  <a href="#quick-start-with-docker">Quick Start</a>
  &nbsp;·&nbsp;
  <a href="#api">API</a>
</p>

<a id="russian"></a>

## Русская версия

LabMate - это fullstack-приложение для лабораторий и небольших исследовательских команд: рабочие пространства, проекты, статьи, задачи, комментарии, командная лента, уведомления и игровая мотивация через виртуального питомца.

Ключевая идея проекта: реальные рабочие действия создают domain events, а уже backend начисляет опыт, монеты и события активности. Frontend не начисляет XP напрямую.

```text
Project / Article / Task mutation
        -> DomainEvent
        -> inline handler or Taskiq worker
        -> Reward, Pet XP/coins, Activity feed, Notifications
```

### Возможности

- Регистрация, вход, refresh/logout и опциональное подтверждение email кодом.
- Рабочие пространства с join-code, ролями участников и приглашениями.
- Kanban-подход для проектов, статей и задач.
- Личные и командные задачи, исполнители, дедлайны, комментарии и упоминания.
- Activity feed и уведомления по задачам, дедлайнам и mentions.
- Workspace wall: посты, реакции, картинки, жалобы и presence.
- Виртуальный питомец: XP, уровни, настроение, голод, энергия, ежедневные награды.
- Игровая экономика: монеты, магазин, еда, шапки, декор, кейсы и инвентарь.
- Мини-игры: daily Sudoku и Zip с leaderboard.
- Статический frontend без npm-сборки, который может работать отдельно от API или отдаваться тем же FastAPI-сервисом.

### Технологии и библиотеки

| Слой | Используется |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| API / schemas | Pydantic v2, pydantic-settings, pydantic[email] |
| Database | PostgreSQL 15, SQLAlchemy 2 async ORM, asyncpg, Alembic |
| Auth | JWT через python-jose[cryptography], bcrypt |
| Forms / uploads | python-multipart |
| Background jobs | Redis 7, Taskiq, taskiq-redis, taskiq-fastapi |
| Frontend | Vanilla HTML/CSS/JavaScript SPA, Fetch API, localStorage |
| Static assets | локальные PNG-ассеты персонажей, шапок, еды, декора и emotes; Twemoji CDN fallback для части иконок |
| Dev / tests | pytest, pytest-asyncio, HTTPX, aiosqlite, Ruff |
| Infra | Docker, Docker Compose, nginx для локального frontend-контейнера |

В репозитории нет `package.json`: основной frontend не использует React/Vite/Webpack и не требует `npm install`.

### Структура проекта

```text
labmate/
├── backend/
│   ├── app/
│   │   ├── api/routers/       # auth, workspaces, projects, articles, tasks, comments, feed, wall, games, pets, shop
│   │   ├── core/              # config, database, security
│   │   ├── services/          # domain logic, events, gamification, email, games
│   │   ├── main.py            # FastAPI app, CORS, routers, static frontend mount
│   │   ├── models.py          # SQLAlchemy entities
│   │   ├── schemas.py         # compatibility exports for Pydantic contracts
│   │   ├── schemas_core.py    # auth, users, pet, games, workspace, project schemas
│   │   ├── schemas_work.py    # articles, tasks, comments, notifications, wall schemas
│   │   └── worker.py          # Taskiq broker/task entrypoint
│   ├── migrations/            # Alembic migrations
│   ├── tests/                 # pytest suite
│   └── pyproject.toml
├── frontend/
│   ├── index.html             # main SPA
│   ├── app.js                 # minified static SPA runtime
│   ├── api.js                 # API client with JWT refresh
│   ├── wireframes.js          # minified prototype/runtime helpers
│   ├── wireframes.css         # visual system
│   ├── assets/                # characters, hats, decor, food, pickups, emotes
│   └── hat-tuner.html/js      # development tool for hat placement
├── docs/technical-spec.md
├── docker-compose.yml
└── Dockerfile                 # single-image deployment
```

### Быстрый старт через Docker

```bash
cp .env.example .env
docker compose up -d --build
```

После запуска:

| URL | Назначение |
| --- | --- |
| http://localhost:5500 | Frontend через nginx |
| http://localhost:8000/docs | Swagger / OpenAPI |
| http://localhost:8000/health | Healthcheck |
| localhost:5433 | PostgreSQL на host-машине |
| localhost:6379 | Redis |

Полезные команды:

```bash
docker compose ps
docker compose logs -f backend worker
docker compose down
docker compose down -v
```

В Docker Compose `EVENT_MODE=taskiq`, поэтому domain events обрабатывает отдельный `worker`.

### Локальная разработка без полного Docker-стека

Поднимите только PostgreSQL и Redis:

```bash
docker compose up -d postgres redis
```

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Worker опционален. Для обычной разработки можно оставить `EVENT_MODE=inline`; для режима очереди:

```bash
cd backend
taskiq worker app.worker:broker
```

Frontend:

```bash
cd frontend
python -m http.server 5500
```

Откройте `http://localhost:5500`. `frontend/api.js` сам выберет `http://localhost:8000/api` для локального static server или `/api`, если frontend отдается тем же origin.

### Конфигурация

Основные переменные:

| Переменная | Назначение |
| --- | --- |
| `DATABASE_URL` | async SQLAlchemy URL, например `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis broker URL |
| `JWT_SECRET` | секрет подписи JWT, обязательно заменить в production |
| `CORS_ORIGINS` | список origin для браузерных запросов |
| `EVENT_MODE` | `inline` или `taskiq` |
| `REQUIRE_EMAIL_VERIFICATION` | требовать код подтверждения email |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | SMTP-настройки |
| `FRONTEND_DIR` | директория статики, если FastAPI отдает frontend |

Если SMTP не настроен, dev-код подтверждения пишется в backend-логи и возвращается в dev-ответе.

### API

Все бизнес-роуты подключены под `/api`.

| Группа | Примеры |
| --- | --- |
| Auth | `/api/auth/register`, `/api/auth/verify`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me` |
| Workspaces | `/api/workspaces`, `/api/workspaces/join`, `/api/workspaces/{id}/members` |
| Projects | `/api/workspaces/{id}/projects`, `/api/projects/{id}`, `/api/projects/{id}/status` |
| Articles | `/api/workspaces/{id}/articles`, `/api/articles/{id}`, `/api/articles/{id}/members` |
| Tasks | `/api/tasks`, `/api/tasks/{id}/complete`, `/api/me/tasks`, `/api/me/tasks/personal` |
| Comments | comments for projects, articles and tasks |
| Feed | `/api/workspaces/{id}/activity`, `/api/notifications` |
| Wall | `/api/workspaces/{id}/wall`, reactions, reports, presence |
| Pets / shop | `/api/pets/me`, `/api/shop/items`, `/api/shop/buy`, `/api/shop/equip` |
| Games | `/api/games/sudoku/daily`, `/api/games/sudoku/solve`, `/api/games/zip/daily`, `/api/games/zip/solve` |

Полная интерактивная документация доступна в Swagger: `http://localhost:8000/docs`.

### Тесты и качество

```bash
cd backend
pytest
ruff check .
```

Краткий review snapshot по текущему репозиторию:

- Backend покрыт pytest-набором в `backend/tests`.
- Backend API разделен по роутерам; shop endpoints вынесены в `backend/app/api/routers/shop.py`, а `app.schemas` сохранен как совместимый export.
- Самая большая зона поддержки - buildless frontend: `frontend/app.js` и `frontend/wireframes.js` отдаются как компактные статические runtime-файлы без npm-сборки.
- Frontend активно использует строковый HTML-рендеринг; при развитии проекта стоит постепенно выносить повторяющиеся DOM helpers и санитизацию в отдельные читаемые source-модули.

<a id="english"></a>

## English Version

LabMate is a fullstack application for labs and small research teams: workspaces, projects, articles, tasks, comments, team activity, notifications, and pet-based gamification.

The core design rule is simple: real work creates domain events, and the backend turns those events into rewards, pet XP, coins, feed items, and notifications. The frontend does not grant XP directly.

```text
Project / Article / Task mutation
        -> DomainEvent
        -> inline handler or Taskiq worker
        -> Reward, Pet XP/coins, Activity feed, Notifications
```

### Features

- Registration, login, refresh/logout, and optional email verification by code.
- Workspaces with join codes, member roles, and invitations.
- Kanban-style projects, articles, and tasks.
- Personal and team tasks with assignees, deadlines, comments, and mentions.
- Activity feed and notifications for assignments, deadlines, and mentions.
- Workspace wall with posts, reactions, images, reports, and presence.
- Virtual pet with XP, levels, mood, hunger, energy, and daily rewards.
- Game economy: coins, shop, food, hats, decor, cases, and inventory.
- Daily Sudoku and Zip games with leaderboards.
- Static frontend that can run separately from the API or be served by the FastAPI service.

### Tech Stack and Libraries

| Layer | Used |
| --- | --- |
| Backend | Python 3.11+, FastAPI, Uvicorn |
| API / schemas | Pydantic v2, pydantic-settings, pydantic[email] |
| Database | PostgreSQL 15, SQLAlchemy 2 async ORM, asyncpg, Alembic |
| Auth | JWT with python-jose[cryptography], bcrypt |
| Forms / uploads | python-multipart |
| Background jobs | Redis 7, Taskiq, taskiq-redis, taskiq-fastapi |
| Frontend | Vanilla HTML/CSS/JavaScript SPA, Fetch API, localStorage |
| Static assets | local PNG assets for characters, hats, food, decor, pickups and emotes; Twemoji CDN fallback for some icons |
| Dev / tests | pytest, pytest-asyncio, HTTPX, aiosqlite, Ruff |
| Infra | Docker, Docker Compose, nginx for the local frontend container |

There is no `package.json` in this repository: the main frontend does not use React, Vite, Webpack, or an npm install step.

### Project Structure

```text
labmate/
├── backend/
│   ├── app/
│   │   ├── api/routers/       # auth, workspaces, projects, articles, tasks, comments, feed, wall, games, pets, shop
│   │   ├── core/              # config, database, security
│   │   ├── services/          # domain logic, events, gamification, email, games
│   │   ├── main.py            # FastAPI app, CORS, routers, static frontend mount
│   │   ├── models.py          # SQLAlchemy entities
│   │   ├── schemas.py         # compatibility exports for Pydantic contracts
│   │   ├── schemas_core.py    # auth, users, pet, games, workspace, project schemas
│   │   ├── schemas_work.py    # articles, tasks, comments, notifications, wall schemas
│   │   └── worker.py          # Taskiq broker/task entrypoint
│   ├── migrations/            # Alembic migrations
│   ├── tests/                 # pytest suite
│   └── pyproject.toml
├── frontend/
│   ├── index.html             # main SPA
│   ├── app.js                 # minified static SPA runtime
│   ├── api.js                 # API client with JWT refresh
│   ├── wireframes.js          # minified prototype/runtime helpers
│   ├── wireframes.css         # visual system
│   ├── assets/                # characters, hats, decor, food, pickups, emotes
│   └── hat-tuner.html/js      # development tool for hat placement
├── docs/technical-spec.md
├── docker-compose.yml
└── Dockerfile                 # single-image deployment
```

### Quick Start with Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Available services:

| URL | Purpose |
| --- | --- |
| http://localhost:5500 | Frontend through nginx |
| http://localhost:8000/docs | Swagger / OpenAPI |
| http://localhost:8000/health | Healthcheck |
| localhost:5433 | PostgreSQL on the host |
| localhost:6379 | Redis |

Useful commands:

```bash
docker compose ps
docker compose logs -f backend worker
docker compose down
docker compose down -v
```

Docker Compose uses `EVENT_MODE=taskiq`, so domain events are processed by the separate `worker` service.

### Local Development

Start only PostgreSQL and Redis:

```bash
docker compose up -d postgres redis
```

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The worker is optional for local work. Keep `EVENT_MODE=inline` for the simple path, or run the queue worker:

```bash
cd backend
taskiq worker app.worker:broker
```

Frontend:

```bash
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500`. `frontend/api.js` automatically uses `http://localhost:8000/api` for the local static server and `/api` when frontend and backend share one origin.

### Configuration

Important environment variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | async SQLAlchemy URL, for example `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis broker URL |
| `JWT_SECRET` | JWT signing secret; replace it in production |
| `CORS_ORIGINS` | browser origins allowed to call the API |
| `EVENT_MODE` | `inline` or `taskiq` |
| `REQUIRE_EMAIL_VERIFICATION` | require email confirmation before login |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | SMTP settings |
| `FRONTEND_DIR` | static frontend directory when served by FastAPI |

If SMTP is not configured, the dev verification code is written to backend logs and returned in the development response.

### API

All business routes are mounted under `/api`.

| Group | Examples |
| --- | --- |
| Auth | `/api/auth/register`, `/api/auth/verify`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/me` |
| Workspaces | `/api/workspaces`, `/api/workspaces/join`, `/api/workspaces/{id}/members` |
| Projects | `/api/workspaces/{id}/projects`, `/api/projects/{id}`, `/api/projects/{id}/status` |
| Articles | `/api/workspaces/{id}/articles`, `/api/articles/{id}`, `/api/articles/{id}/members` |
| Tasks | `/api/tasks`, `/api/tasks/{id}/complete`, `/api/me/tasks`, `/api/me/tasks/personal` |
| Comments | comments for projects, articles, and tasks |
| Feed | `/api/workspaces/{id}/activity`, `/api/notifications` |
| Wall | `/api/workspaces/{id}/wall`, reactions, reports, presence |
| Pets / shop | `/api/pets/me`, `/api/shop/items`, `/api/shop/buy`, `/api/shop/equip` |
| Games | `/api/games/sudoku/daily`, `/api/games/sudoku/solve`, `/api/games/zip/daily`, `/api/games/zip/solve` |

The full interactive API reference is available at `http://localhost:8000/docs`.

### Tests and Quality

```bash
cd backend
pytest
ruff check .
```

Current repository review snapshot:

- The backend has a pytest suite in `backend/tests`.
- The backend API is split by routers; shop endpoints live in `backend/app/api/routers/shop.py`, while `app.schemas` remains a compatibility export.
- The main maintainability risk is the buildless frontend: `frontend/app.js` and `frontend/wireframes.js` are compact static runtime files without an npm build step.
- The frontend relies heavily on string-based HTML rendering; as the project grows, move repeated DOM helpers and sanitization into readable source modules.
