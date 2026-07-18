import hashlib
import uuid
from datetime import UTC, datetime

from src.application.exceptions import ConflictError, ValidationError
from src.application.job.ports import JobProcessingDispatcher
from src.domain.job.entities import Job, JobLifecycleStatus, JobProcessingStatus, Location
from src.domain.job.repository import JobRepository

PARSER_VERSION = "v1"

_UPDATE_FIELDS = frozenset(
    {
        "title",
        "raw_description",
        "summary",
        "required_skills",
        "nice_to_have_skills",
        "responsibilities",
        "qualifications",
        "min_experience_years",
        "employment_type",
        "work_mode",
        "location",
        "salary_min",
        "salary_max",
    }
)


def _hash_description(raw_description: str) -> str:
    return hashlib.sha256(raw_description.encode()).hexdigest()


class JobService:
    def __init__(self, job_repo: JobRepository, dispatcher: JobProcessingDispatcher) -> None:
        self._jobs = job_repo
        self._dispatcher = dispatcher

    def create_job(
        self, company_id: uuid.UUID, user_id: uuid.UUID, title: str, raw_description: str
    ) -> Job:
        now = datetime.now(UTC)
        job = Job(
            id=uuid.uuid4(),
            company_id=company_id,
            created_by_user_id=user_id,
            title=title,
            raw_description=raw_description,
            summary=None,
            required_skills=[],
            nice_to_have_skills=[],
            responsibilities=[],
            qualifications=[],
            min_experience_years=None,
            employment_type=None,
            work_mode=None,
            location=Location(),
            salary_min=None,
            salary_max=None,
            lifecycle_status=JobLifecycleStatus.DRAFT,
            processing_status=JobProcessingStatus.PENDING,
            parser_version=PARSER_VERSION,
            content_hash=_hash_description(raw_description),
            error_message=None,
            version=1,
            published_at=None,
            closed_at=None,
            parsed_at=None,
            created_at=now,
            updated_at=now,
        )
        job = self._jobs.add(job)
        self._dispatcher.dispatch_parse(job.id)
        return job

    def list_jobs(self, company_id: uuid.UUID) -> list[Job]:
        return self._jobs.list_by_company(company_id)

    def update_job(self, job: Job, updates: dict[str, object]) -> Job:
        """`job` must already be loaded and authorization-checked by the caller (see
        `require_job_membership` in api/deps.py) — this only applies the whitelisted field
        changes and re-triggers parsing if `raw_description` actually changed."""
        unknown_fields = set(updates) - _UPDATE_FIELDS
        if unknown_fields:
            raise ValidationError(f"Unknown job field(s): {', '.join(sorted(unknown_fields))}")

        description_changed = False
        if "raw_description" in updates:
            new_description = str(updates["raw_description"])
            new_hash = _hash_description(new_description)
            if new_hash != job.content_hash:
                job.raw_description = new_description
                job.content_hash = new_hash
                description_changed = True
            del updates["raw_description"]

        for field_name, value in updates.items():
            setattr(job, field_name, value)

        job.updated_at = datetime.now(UTC)

        if description_changed:
            job.version += 1
            job.processing_status = JobProcessingStatus.PENDING
            job.error_message = None
            job = self._jobs.update(job)
            self._dispatcher.dispatch_parse(job.id)
            return job

        return self._jobs.update(job)

    def delete_job(self, job: Job) -> None:
        if job.lifecycle_status != JobLifecycleStatus.DRAFT:
            raise ConflictError("Only draft jobs can be deleted")
        self._jobs.delete(job.id)

    def publish_job(self, job: Job) -> Job:
        if job.lifecycle_status != JobLifecycleStatus.DRAFT:
            raise ConflictError("Only draft jobs can be published")
        if job.processing_status != JobProcessingStatus.READY:
            raise ValidationError("Job must finish processing before it can be published")
        job.lifecycle_status = JobLifecycleStatus.PUBLISHED
        job.published_at = datetime.now(UTC)
        job.updated_at = job.published_at
        return self._jobs.update(job)

    def close_job(self, job: Job) -> Job:
        if job.lifecycle_status != JobLifecycleStatus.PUBLISHED:
            raise ConflictError("Only published jobs can be closed")
        job.lifecycle_status = JobLifecycleStatus.CLOSED
        job.closed_at = datetime.now(UTC)
        job.updated_at = job.closed_at
        return self._jobs.update(job)

    def reopen_job(self, job: Job) -> Job:
        if job.lifecycle_status != JobLifecycleStatus.CLOSED:
            raise ConflictError("Only closed jobs can be reopened")
        job.lifecycle_status = JobLifecycleStatus.PUBLISHED
        job.published_at = datetime.now(UTC)
        job.closed_at = None
        job.updated_at = job.published_at
        return self._jobs.update(job)
