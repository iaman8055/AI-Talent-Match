from sqlalchemy.orm import Session

from src.application.job.service import JobService
from src.application.scraping.linkedin_ingestion_service import LinkedInIngestionService
from src.core.config import get_settings
from src.infrastructure.db.repositories import (
    SqlAlchemyCompanyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyUserRepository,
)
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.scraping.linkedin_client import LinkedInGuestClient
from src.infrastructure.tasks.celery_app import celery_app
from src.infrastructure.tasks.job_tasks import CeleryJobDispatcher
from src.infrastructure.tasks.matching_tasks import CeleryMatchingDispatcher

settings = get_settings()

# Stateless — safe to share across task invocations, same discipline as job_tasks.py.
_scraper_client = LinkedInGuestClient()
_job_dispatcher = CeleryJobDispatcher()
_matching_dispatcher = CeleryMatchingDispatcher()

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 3,
}


def _build_ingestion_service(session: Session) -> LinkedInIngestionService:
    job_repo = SqlAlchemyJobRepository(session)
    return LinkedInIngestionService(
        job_repo=job_repo,
        job_service=JobService(job_repo, _job_dispatcher, _matching_dispatcher),
        scraper_client=_scraper_client,
        company_repo=SqlAlchemyCompanyRepository(session),
        user_repo=SqlAlchemyUserRepository(session),
    )


@celery_app.task(name="run_linkedin_scrape", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def run_linkedin_scrape_task() -> int:
    """Celery Beat entry (every 6h, see celery_app.py). Each created job flows through the
    existing, unmodified dispatch_parse -> parse_job -> embed_job chain — the shared NVIDIA
    rate limiter inside infrastructure/ai/nvidia_client.py is what keeps this from bursting past
    the account's rate limit, not anything in this task."""
    session = SessionLocal()
    try:
        created = _build_ingestion_service(session).ingest(
            settings.linkedin_scrape_queries, settings.linkedin_scrape_max_jobs_per_run
        )
        session.commit()
        return created
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
