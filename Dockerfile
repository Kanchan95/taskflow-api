FROM python:3.11-slim

WORKDIR /app

RUN pip install --upgrade pip && pip install \
    fastapi \
    "uvicorn[standard]" \
    pydantic \
    pydantic-settings \
    "sqlalchemy[asyncio]" \
    asyncpg \
    alembic \
    "redis[hiredis]" \
    "python-jose[cryptography]" \
    "passlib[bcrypt]" \
    "pydantic[email]" \
    python-multipart \
    "celery[redis]" \
    structlog \
    httpx

COPY . .

RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
