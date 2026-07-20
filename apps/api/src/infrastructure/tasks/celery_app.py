from celery import Celery

from src.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_talent_match",
    broker=settings.redis_url,
    backend=settings.redis_url,
    # Explicit include, not autodiscover_tasks(): autodiscover only looks for a nested
    # "tasks" submodule per package (the Django-app convention) — it would silently find
    # nothing here since these are top-level modules (resume_tasks.py, not tasks.py), leaving
    # every task "unregistered" on the worker and every enqueued message silently discarded.
    include=[
        "src.infrastructure.tasks.email_tasks",
        "src.infrastructure.tasks.resume_tasks",
        "src.infrastructure.tasks.job_tasks",
        "src.infrastructure.tasks.matching_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
