"""
Application entry point.

lifespan context manager handles startup/shutdown logic cleanly.
The old @app.on_event("startup") pattern is deprecated in newer FastAPI.
"""
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine
from app.middleware.logging import LoggingMiddleware, configure_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.api.v1 import auth, tasks, health

settings = get_settings()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.DEBUG)
    logger.info("startup", app=settings.APP_NAME)
    yield
    # Graceful shutdown: close DB connection pool
    await engine.dispose()
    logger.info("shutdown", app=settings.APP_NAME)


app = FastAPI(
    title="TaskFlow API",
    description="Production-grade async task management REST API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,  # Disable Swagger in prod
    lifespan=lifespan,
)

# Middleware order matters: outermost runs first on request, last on response
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)
app.include_router(health.router)
