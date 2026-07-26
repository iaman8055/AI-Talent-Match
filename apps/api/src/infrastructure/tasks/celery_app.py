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
        "src.infrastructure.tasks.linkedin_scraper_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Two queues, split by whether a task can block on the shared NVIDIA/HF AI rate limiter.
    # Without this, a single worker (services/worker/main.py's local-dev setup) blocks on
    # everything while one task waits on a rate-limit slot — including cheap, latency-sensitive
    # work like sending a notification email. Once queues are separate, that same worker just
    # needs `-Q heavy,light` (see main.py) to behave exactly as before; splitting into two actual
    # worker processes (one per queue) is then a pure ops change, no code change, and the
    # Redis-backed rate limiter (infrastructure/ai/nvidia_client.py) already makes that safe to
    # scale horizontally.
    task_routes={
        "parse_job": {"queue": "heavy"},
        "embed_job": {"queue": "heavy"},
        "parse_resume": {"queue": "heavy"},
        "embed_resume": {"queue": "heavy"},
        "compute_job_matches": {"queue": "heavy"},
        "compute_candidate_matches": {"queue": "heavy"},
        # its generate_drafts node calls the LLM
        "run_recruiter_agent_for_candidate": {"queue": "heavy"},
        "send_email": {"queue": "light"},
        "run_apply_agent_scan": {"queue": "light"},
        # pure Python, no LLM/embed calls (see agents/apply_agent/graph.py's own docstring)
        "run_apply_agent_for_candidate": {"queue": "light"},
        # HTTP scraping only; dispatches parse_job (heavy) rather than embedding itself
        "run_linkedin_scrape": {"queue": "light"},
    },
    task_default_queue="light",
    # Apply Agent scan (docs/03-ROADMAP.md Phase 6): runs frequently, but each run only picks up
    # jobs published in the last 24h and skips (candidate, job) pairs already decided — see
    # agent_tasks.py and agents/apply_agent/graph.py.
    beat_schedule={
        "apply-agent-scan": {
            "task": "run_apply_agent_scan",
            "schedule": crontab(minute="*/15"),
        },
        # LinkedIn job ingestion (see infrastructure/tasks/linkedin_scraper_tasks.py) — every 6h
        # is deliberately conservative; each run is bounded by the shared NVIDIA rate limiter
        # regardless of cadence, so this mainly controls how fresh the listings stay.
        "linkedin-scrape": {
            "task": "run_linkedin_scrape",
            "schedule": crontab(minute=0, hour="*/6"),
        },
    },
)
