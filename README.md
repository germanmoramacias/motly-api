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
- `GET /api/v1/grammar`
- `POST /api/v1/grammar`
- `GET /api/v1/grammar?lesson_id={lesson_id}`
- `GET /api/v1/expressions`
- `POST /api/v1/expressions`
- `GET /api/v1/expressions?lesson_id={lesson_id}`
- `POST /api/v1/quiz/generate`
- `POST /api/v1/writing/submissions`
- `POST /api/v1/ai/chat`
- `GET /api/v1/analytics/stats`
- `POST /api/v1/analytics/quiz-results`

## Vocabulary And Expressions Search

Both list endpoints accept these optional query parameters:

| Parameter | Behavior |
| --- | --- |
| `q` | Case-insensitive substring search, up to 200 characters. Leading/trailing whitespace is ignored; an empty or whitespace-only value disables search. |
| `lesson_id` | Only return entries linked to this lesson (UUID). |
| `limit` | Page size, from 1 to 5000 (default: 1000). |
| `offset` | Number of matching entries to skip (default: 0). |
| `sort` | `created_at_desc` (default, newest first) or `created_at_asc` (oldest first); `term_asc`/`term_desc` for vocabulary; `text_asc`/`text_desc` for expressions. |

Vocabulary search covers `term`, `definition`, and `example`. Expression search covers
`text`, `meaning`, `example`, `keyword`, and `group`. A match in any field is sufficient.
Search treats `%` and `_` as literal characters, not wildcards. It is not accent-insensitive
or fuzzy search.

```http
GET /api/v1/vocabulary?q=horse&limit=50&offset=0&sort=created_at_desc
GET /api/v1/expressions?q=warm%20up&limit=50&offset=0&sort=created_at_asc
GET /api/v1/vocabulary?limit=50&offset=0&sort=term_asc
GET /api/v1/expressions?limit=50&offset=0&sort=text_desc
GET /api/v1/vocabulary?q=travel&lesson_id={lesson_id}&limit=50&offset=0
```

All filters and ordering apply before pagination and only return the authenticated user's entries.
Alphabetical ordering is case-insensitive and uses the ID as a deterministic tie-breaker.
Both endpoints now return an object instead of the previous bare array. Clients must read entries
from `response.items`:

```json
{
  "items": [],
  "total": 0,
  "total_pages": 0,
  "limit": 50,
  "offset": 0
}
```

`total` counts all matching entries before pagination, including the `q` and `lesson_id` filters.
`total_pages` is `ceil(total / limit)`, or 0 for no matches. An offset beyond the last result returns
empty `items` but preserves the matching total and page count. Entries with identical `created_at`
values are sorted by ID in the same direction to keep ordering deterministic.
No `X-Total-Count` header is returned. Other list endpoints keep their existing response format.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```

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
