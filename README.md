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
- `POST /api/v1/quiz/sessions` (requires `Idempotency-Key`)
- `GET /api/v1/quiz/sessions/active`
- `GET /api/v1/quiz/sessions/{id}`
- `POST /api/v1/quiz/sessions/{id}/answers`
- `POST /api/v1/quiz/sessions/{id}/retry`
- `GET /api/v1/quiz/sessions?status=completed`
- `GET /api/v1/quiz/sources/lessons?q=...&limit=20&offset=0`
- `POST /api/v1/writing/submissions`
- `POST /api/v1/ai/chat`
- `GET /api/v1/analytics/stats`
- `GET /api/v1/analytics/quiz-results` (read-only; new scores are server-derived)

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

## Persistent quizzes

Apply `alembic upgrade head` before deploying the updated API and worker. For Supabase,
use the existing PostgreSQL database connection. The migration creates four tables,
adds nullable fields to legacy results, and enables RLS on the new tables with no
client policies. API/worker database credentials must have backend access (table owner
or an appropriate server-only role). Never grant frontend roles access to answer keys.
No existing study material or legacy scores are rewritten.

Run `python -m app.modules.quiz.worker` alongside uvicorn, or start the `quiz-worker`
service in either Compose configuration. Deploy both processes from the same version.
The worker uses PostgreSQL row locks and expiring job leases, without Redis or pgmq.
It does not hold database locks while calling the model. A terminated worker's job
can be reclaimed; fencing tokens prevent late publication by its previous owner.
Generation may call the provider again after interruption; publication is idempotent.

Create with `{"scope":"all"}` or `{"scope":"lesson","lesson_id":"UUID"}`.
The same idempotency key and payload return the original session, even after completion.
A different request while a quiz is pending returns `409 ACTIVE_QUIZ_EXISTS`.
Only the current question and already submitted answers are exposed. Answer with
`{"question_id":"UUID","selected_option_id":"UUID"}`. Replaying the same answer is
safe; changing a submitted answer returns 409. The last answer atomically completes
the session and writes its verified analytics summary. There is no client completion
or score-submission endpoint. `score` on new legacy-compatible summaries is the count
of correct answers; `score_percent` is the normalized percentage. Analytics averages
verified percentages and excludes legacy entries whose score scale is unknown.

All scope uses a bounded diverse sample of the user's saved material, including
unlinked WordLab/grammar entries, rotating away from recently used sources. It does
not test every item in every quiz. Snapshots remove HTML, scripts and embedded images;
image-only notes are not supported. Model output is schema-validated and checked for
unknown sources, duplicate questions and invalid options before publication.
The model picks 1–15 questions (configurable upper bound); no client count is accepted.

The old stateless `/quiz/generate` and client-write `/analytics/quiz-results` routes
are removed. Frontend clients must migrate together. Local demo history is not imported.

Quiz tests run on an isolated SQLite database by default (`pip install -e ".[dev]"`).
Set `QUIZ_TEST_DATABASE_URL` to a disposable PostgreSQL database to additionally test
row-lock concurrency. Each test creates and drops its own randomly named schema.
The test workflow runs migrations and the full suite against PostgreSQL 16.

Production activation and rollback procedures are in [docs/quiz-operations.md](docs/quiz-operations.md).
The 0005 downgrade archives quiz data privately rather than deleting it; upgrading
again restores it. Deployment retains the previous image and a private application-data
backup, with a code-only rollback as the default recovery path.
