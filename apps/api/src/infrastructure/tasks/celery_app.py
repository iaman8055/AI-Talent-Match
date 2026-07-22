from celery import Celery
from celery.schedules import crontab

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
        "src.infrastructure.tasks.agent_tasks",
        "src.infrastructure.tasks.recruiter_agent_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Apply Agent scan (docs/03-ROADMAP.md Phase 6): runs frequently, but each run only picks up
    # jobs published in the last 24h and skips (candidate, job) pairs already decided — see
    # agent_tasks.py and agents/apply_agent/graph.py.
    beat_schedule={
        "apply-agent-scan": {
            "task": "run_apply_agent_scan",
            "schedule": crontab(minute="*/15"),
        },
    },
)
