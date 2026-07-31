"""
Async SQLAlchemy setup.

Key ideas:
- AsyncEngine + AsyncSession = no thread blocking during DB I/O
- Connection pool (pool_size + max_overflow) avoids creating a new TCP connection
  per request — TCP handshake + auth is expensive at scale
- expire_on_commit=False keeps objects usable after commit without a reload query
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DEBUG,  # logs SQL in dev; never in prod (leaks data)
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a session per request, always closes it."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
