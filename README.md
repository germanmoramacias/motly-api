# Motly API

Async FastAPI backend for an AI-powered English learning app. It is organized as a modular monolith so modules can be split into independent services later without mixing responsibilities.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy 2.0 async
- Alembic
- Supabase PostgreSQL
- Pydantic v2
- OpenAI SDK async
- JWT Authentication con Supabase
- Docker
- uv

## Structure

```text
app/
  core/          # configuration, logging, errors, routing
  db/            # engine async, sesiones, base declarativa
  middleware/    # auth middleware
  modules/       # bounded contexts del monolito modular
  shared/        # schemas/base primitives/security
  utils/         # small utilities
  main.py
```

Each module contains `router.py`, `service.py`, `repository.py`, `schemas.py`, and `models.py`.

## Configuration

```bash
cp .env.example .env
```

Configure:

- `DATABASE_URL`
- `SUPABASE_JWKS_URL`
- `SUPABASE_JWT_ISSUER`
- `SUPABASE_JWT_AUDIENCE`
- `OPENAI_API_KEY`
- `BACKEND_CORS_ORIGINS`

For Supabase, use an async URL:

```env
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<host>:5432/postgres
```

## Local Development With uv

```bash
uv venv --python 3.12
uv pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Healthcheck:

```bash
curl http://localhost:8000/api/v1/health
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

In another terminal:

```bash
docker compose exec api alembic upgrade head
```

## Authentication

Los endpoints protegidos esperan:

```http
Authorization: Bearer <supabase_access_token>
```

The middleware validates the JWT against Supabase JWKS and exposes the claims in `request.state.user`. The `GET /api/v1/users/me` endpoint creates the local user if it does not exist yet.

## Main Endpoints

- `GET /api/v1/health`
- `GET /api/v1/auth/me`
- `GET /api/v1/users/me`
- `PATCH /api/v1/users/{user_id}`
- `GET /api/v1/notes`
- `POST /api/v1/notes`
- `GET /api/v1/notes/{lesson_id}`
- `PATCH /api/v1/notes/{lesson_id}`
- `DELETE /api/v1/notes/{lesson_id}`
- `GET /api/v1/vocabulary`
- `POST /api/v1/vocabulary`
- `GET /api/v1/vocabulary?lesson_id={lesson_id}`
- `POST /api/v1/grammar/lessons/{lesson_id}/extract`
- `GET /api/v1/expressions`
- `POST /api/v1/expressions`
- `GET /api/v1/expressions?lesson_id={lesson_id}`
- `POST /api/v1/quiz/generate`
- `POST /api/v1/writing/submissions`
- `POST /api/v1/ai/tutor-chat`
- `GET /api/v1/analytics/stats`
- `POST /api/v1/analytics/quiz-results`

## Alembic

Create a migration:

```bash
alembic revision --autogenerate -m "message"
```

Apply migrations:

```bash
alembic upgrade head
```

## Architecture Notes

- Routers only handle HTTP validation and delegate to services.
- Services contain application logic.
- Repositories encapsulate SQLAlchemy access.
- Configuration is centralized in `app/core/config.py`.
- Global errors live in `app/core/errors.py`.
- The OpenAI integration lives in `app/modules/ai/service.py`.
