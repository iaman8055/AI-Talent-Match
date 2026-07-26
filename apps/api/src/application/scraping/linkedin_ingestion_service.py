import logging

from src.application.job.service import JobService
from src.application.scraping.ports import JobScraperClient
from src.application.scraping.system_account import ensure_system_account
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import JobSource
from src.domain.job.repository import JobRepository
from src.domain.user.repository import UserRepository

logger = logging.getLogger(__name__)

_MAX_DESCRIPTION_CHARS = 20000  # matches CreateJobRequest's max_length (api/v1/jobs/schemas.py)


class LinkedInIngestionService:
    """Invoked from a Celery task (infrastructure/tasks/linkedin_scraper_tasks.py), never from a
    request-handling code path. Creates Job rows exactly like the recruiter-facing API does
    (via JobService.create_job) so the existing parse -> embed -> auto-publish pipeline (see
    application/job/parsing_service.py) requires no scraper-specific branch."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_service: JobService,
        scraper_client: JobScraperClient,
        company_repo: CompanyRepository,
        user_repo: UserRepository,
    ) -> None:
        self._jobs = job_repo
        self._job_service = job_service
        self._scraper = scraper_client
        self._companies = company_repo
        self._users = user_repo

    def ingest(self, queries: list[str], max_jobs_per_run: int) -> int:
        company, user = ensure_system_account(self._companies, self._users)

        created = 0
        seen_ids: set[str] = set()
        for query in queries:
            if created >= max_jobs_per_run:
                break
            for job_id in self._scraper.search_job_ids(query, max_results=max_jobs_per_run):
                if created >= max_jobs_per_run or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                if self._jobs.get_by_source_and_external_id(JobSource.LINKEDIN, job_id):
                    continue

                posting = self._scraper.fetch_job_detail(job_id)
                if posting is None:
                    continue

                try:
                    self._job_service.create_job(
                        company_id=company.id,
                        user_id=user.id,
                        title=posting["title"][:200],
                        raw_description=posting["raw_description"][:_MAX_DESCRIPTION_CHARS],
                        source=JobSource.LINKEDIN,
                        external_id=posting["external_id"],
                        external_url=posting["url"],
                        external_company_name=posting["company_name"],
                    )
                    created += 1
                except Exception:
                    logger.warning("Failed to ingest LinkedIn job %s", job_id, exc_info=True)

        return created
