"""
Structured JSON logging with structlog.

Why JSON logs? In production you ship logs to Elasticsearch/Datadog/CloudWatch.
Those systems parse JSON natively — structured fields (request_id, status_code,
duration_ms) are searchable/filterable. Free-text logs are not.
"""
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.middleware.request_id import request_id_var

logger = structlog.get_logger()


def configure_logging(debug: bool = False) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10 if debug else 20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id_var.get(),
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
