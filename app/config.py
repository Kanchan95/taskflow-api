"""
12-factor app configuration: all settings come from environment variables.
pydantic-settings validates types and provides defaults, making config
self-documenting and fail-fast at startup if required values are missing.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    APP_NAME: str = "taskflow-api"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database — async driver (asyncpg) for non-blocking I/O
    DATABASE_URL: str = "postgresql+asyncpg://taskflow:taskflow@localhost:5432/taskflow"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Redis — rate limiting, caching, Celery broker
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_REQUESTS: int = 100   # requests per window
    RATE_LIMIT_WINDOW: int = 60      # seconds

    # Auth
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"


@lru_cache
def get_settings() -> Settings:
    # Cached so the .env file is read once, not on every request
    return Settings()
