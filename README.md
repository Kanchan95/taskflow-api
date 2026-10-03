# TaskFlow API

An async task management REST API built with FastAPI, SQLAlchemy (asyncpg),
PostgreSQL, Redis and Celery.

---

## What is Built

A JWT-authenticated REST API for managing tasks. Users register, log in, and
get a token. They use that token to create, list, update, and delete their tasks.
Background jobs (Celery) send notifications asynchronously without blocking
the HTTP response.

---

## Architecture Overview

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────────────────────┐
│  Middleware Stack (runs on every request, in order)  │
│  1. CORSMiddleware    → browser cross-origin policy  │
│  2. RequestIDMiddleware → inject UUID trace ID       │
│  3. LoggingMiddleware   → structured JSON log line   │
│  4. RateLimitMiddleware → Redis-based IP throttle    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
              FastAPI Router
           /api/v1/auth   /api/v1/tasks   /health   /ready
                     │
                     ▼
           Dependency Injection (get_db, get_current_user)
                     │
               Service Layer
          (auth_service, task_service)
                     │
                     ▼
         Async SQLAlchemy → PostgreSQL
         Celery Task Queue → Redis → Worker Process
```

---

## Key Patterns Used

### 1. Async all the way down
Every DB call is `await`-ed. The web server (uvicorn) runs an event loop that
handles thousands of concurrent requests on a single thread — no thread-per-
request waste. `asyncpg` is the async PostgreSQL driver; `aiosqlite` for tests.

### 2. Pydantic Settings (12-factor config)
`app/config.py` — all configuration comes from environment variables. The app
fails fast at startup if a required variable is missing. No hardcoded values.

### 3. Middleware chain
Each middleware is a wrapper around the next one (like onion layers):
- **RequestID**: injects a UUID into every request for end-to-end tracing
- **Logging**: logs method, path, status, duration_ms as a JSON line
- **RateLimit**: Redis counter per IP per time window → 429 if exceeded

### 4. JWT Auth (stateless)
No server-side sessions. The token carries the user_id signed with a secret.
Verification is pure computation — no DB lookup needed to validate a token.
`app/api/deps.py` — single `get_current_user` dependency injected everywhere.

### 5. Service layer
Routes are thin; all business logic lives in `app/services/`. This makes it
easy to test logic without HTTP overhead and reuse logic across routes.

### 6. Celery background workers
`send_task_notification.delay(...)` queues a job in Redis and returns
immediately. A separate worker process picks it up and runs it. This pattern
is critical for operations that are slow (email, PDF generation, ML inference).

### 7. Health checks (liveness vs readiness)
- `GET /health` — liveness: is the process running? K8s restarts if this fails
- `GET /ready` — readiness: can it serve traffic? Checks DB + Redis. K8s removes
  the pod from the load balancer if this fails (but doesn't restart it)

### 8. Multi-stage Docker build
Builder stage installs packages; runtime stage is lean (no pip, no build tools).
Final image runs as a non-root user for security.

### 9. Database migrations (Alembic)
Schema changes are versioned scripts. `alembic upgrade head` applies all pending
migrations. `alembic revision --autogenerate` auto-generates migration from model
changes. Never use `Base.metadata.create_all()` in production.

### 10. Testing with dependency override
`tests/conftest.py` swaps PostgreSQL with SQLite in-memory via
`app.dependency_overrides[get_db]`. No Docker required for tests. Fast and
isolated — each test gets a rolled-back session.

---

## Project Structure

```
taskflow-api/
├── app/
│   ├── main.py              # FastAPI app + lifespan + middleware setup
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── database.py          # Async SQLAlchemy engine + session
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   └── task.py
│   ├── schemas/             # Pydantic request/response models
│   │   ├── auth.py
│   │   └── task.py
│   ├── middleware/          # Custom ASGI middleware
│   │   ├── request_id.py
│   │   ├── logging.py
│   │   └── rate_limit.py
│   ├── api/
│   │   ├── deps.py          # get_db, get_current_user dependencies
│   │   └── v1/
│   │       ├── auth.py      # /register, /login
│   │       ├── tasks.py     # CRUD endpoints
│   │       └── health.py    # /health, /ready
│   ├── services/            # Business logic (no HTTP concerns)
│   │   ├── auth_service.py
│   │   └── task_service.py
│   └── workers/
│       └── celery_app.py    # Celery tasks
├── migrations/              # Alembic migration scripts
├── tests/
│   ├── conftest.py          # Fixtures, test DB, auth client
│   ├── test_auth.py
│   └── test_tasks.py
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Local dev: API + Worker + PG + Redis
├── Makefile                 # Common commands
├── pyproject.toml           # Dependencies + tooling config
└── alembic.ini
```

---

## How to Run

### Local (with Docker)
```bash
cp .env.example .env
make dev           # starts API + worker + postgres + redis
# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs (DEBUG=true only)
```

### Run Tests
```bash
pip install -e ".[dev]"
make test
```

### Run a Migration
```bash
make migrate
# or create a new one:
make new-migration name="add_due_date_to_tasks"
```

---

## API Quick Reference

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Get JWT token |
| GET | `/api/v1/tasks/` | List tasks (paginated, filterable) |
| POST | `/api/v1/tasks/` | Create task |
| GET | `/api/v1/tasks/{id}` | Get single task |
| PATCH | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Delete task |
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check (DB + Redis) |

