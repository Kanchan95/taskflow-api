"""
Kubernetes uses two probes:
- Liveness (/health): Is the process alive? If this fails, K8s restarts the pod.
- Readiness (/ready): Can it serve traffic? If this fails, K8s removes the pod
  from the load balancer but doesn't restart it.

A pod can be alive but not ready (e.g., still running DB migrations).
"""
import redis.asyncio as aioredis
from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.database import AsyncSessionLocal

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def readiness():
    checks = {}
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return {"status": "ok" if all_ok else "degraded", "checks": checks}
