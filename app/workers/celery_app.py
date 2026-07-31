"""
Celery background worker.

Why a separate worker process? Some operations shouldn't block the HTTP
response — sending emails, push notifications, generating reports, etc.
Celery picks tasks off a Redis queue and runs them in separate worker
processes, so the API returns immediately.

Run the worker: celery -A app.workers.celery_app worker --loglevel=info
"""
import structlog
from celery import Celery
from app.config import get_settings

settings = get_settings()
logger = structlog.get_logger()

celery = Celery(
    "taskflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_track_started=True,
    task_acks_late=True,  # Only ack after success — ensures at-least-once delivery
)


@celery.task(bind=True, max_retries=3)
def send_task_notification(self, user_email: str, task_id: int, action: str):
    """Simulates sending an email/push notification. Retries up to 3× on failure."""
    try:
        logger.info("sending_notification", email=user_email, task_id=task_id, action=action)
        # In real code: call an email service (SES, SendGrid, etc.)
        logger.info("notification_sent", email=user_email)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2**self.request.retries)
