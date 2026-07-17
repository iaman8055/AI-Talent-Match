from celery import Celery

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_talent_match",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Task modules are registered here as they're added, starting Phase 2
# (resume parsing / embedding). None exist yet in Phase 0.
celery_app.autodiscover_tasks(["src.infrastructure.tasks"])
