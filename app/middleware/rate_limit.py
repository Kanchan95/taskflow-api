"""
Sliding-window rate limiter backed by Redis.

Why Redis and not in-memory? In-memory counters reset when a pod restarts
and don't work across multiple API replicas. Redis is a shared, persistent
counter store — works identically whether you have 1 pod or 20.

Algorithm: fixed window (simpler). Each key = f"rate:{ip}:{window_bucket}"
where window_bucket = int(now / window_size). Expire the key after 2 windows
so Redis cleans up automatically.
"""
import time
import redis.asyncio as aioredis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        self.limit = settings.RATE_LIMIT_REQUESTS
        self.window = settings.RATE_LIMIT_WINDOW

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        window_bucket = int(time.time() / self.window)
        key = f"rate:{client_ip}:{window_bucket}"

        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, self.window * 2)

        remaining = max(0, self.limit - count)
        if count > self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(self.window),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
