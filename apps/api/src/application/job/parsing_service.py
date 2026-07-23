import uuid
from datetime import UTC, datetime

from src.application.ai.ports import EmbeddingClient, LLMClient, VectorStore
from src.application.job.extraction_schema import JOB_EXTRACTION_INSTRUCTIONS, JobExtractionResult
from src.application.matching.ports import MatchingDispatcher
from src.domain.job.entities import Job, JobProcessingStatus, JobVersion, Location, WorkMode
from src.domain.job.repository import JobRepository, JobVersionRepository

JOBS_COLLECTION = "jobs"
_MAX_TEXT_CHARS = 8000


def _clean_job_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned[:_MAX_TEXT_CHARS]


def _build_embedding_text(job: Job) -> str:
    parts = [
        job.title,
        job.summary or "",
        ", ".join(job.required_skills),
        " ".join(job.responsibilities),
    ]
    return "\n".join(part for part in parts if part)[:_MAX_TEXT_CHARS]


def _apply_extraction(job: Job, result: JobExtractionResult) -> None:
    if result.summary:
        job.summary = result.summary
    if result.required_skills:
        job.required_skills = result.required_skills
    if result.nice_to_have_skills:
        job.nice_to_have_skills = result.nice_to_have_skills
    if result.responsibilities:
        job.responsibilities = result.responsibilities
    if result.qualifications:
        job.qualifications = result.qualifications
    if result.min_experience_years is not None:
        job.min_experience_years = result.min_experience_years
    if result.employment_type:
        job.employment_type = result.employment_type
    if result.work_mode:
        try:
            job.work_mode = WorkMode(result.work_mode)
        except ValueError:
            pass
    if any([result.location_country, result.location_region, result.location_city]):
        job.location = Location(
            country=result.location_country,
            region=result.location_region,
            city=result.location_city,
        )
    if result.salary_min is not None:
        job.salary_min = result.salary_min
    if result.salary_max is not None:
        job.salary_max = result.salary_max


class JobParsingService:
    """Invoked from Celery tasks (infrastructure/tasks/job_tasks.py), never from a
    request-handling code path — matches the architecture doc's async-AI-pipeline rule."""

    def __init__(
        self,
        job_repo: JobRepository,
        job_version_repo: JobVersionRepository,
        llm_client: LLMClient,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        matching_dispatcher: MatchingDispatcher,
    ) -> None:
        self._jobs = job_repo
        self._job_versions = job_version_repo
        self._llm = llm_client
        self._embeddings = embedding_client
        self._vector_store = vector_store
        self._matching_dispatcher = matching_dispatcher

    def parse_job(self, job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            return

        job.processing_status = JobProcessingStatus.PARSING
        self._jobs.update(job)

        try:
            cleaned_text = _clean_job_text(job.raw_description)
            result = self._llm.extract_structured(
                JOB_EXTRACTION_INSTRUCTIONS, cleaned_text, JobExtractionResult
            )

            _apply_extraction(job, result)

            parsed_at = datetime.now(UTC)
            job.processing_status = JobProcessingStatus.PARSED
            job.parsed_at = parsed_at
            job.error_message = None
            job = self._jobs.update(job)

            self._job_versions.add(
                JobVersion(
                    id=uuid.uuid4(),
                    job_id=job.id,
                    version=job.version,
                    raw_description=job.raw_description,
                    content_hash=job.content_hash,
                    parser_version=job.parser_version or "v1",
                    extracted_snapshot=result.model_dump(),
                    created_at=parsed_at,
                )
            )
        except Exception as exc:
            job.processing_status = JobProcessingStatus.FAILED
            job.error_message = str(exc)[:500]
            self._jobs.update(job)
            raise

    def embed_job(self, job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            return

        job.processing_status = JobProcessingStatus.EMBEDDING
        self._jobs.update(job)

        try:
            embedding_text = _build_embedding_text(job)
            [vector] = self._embeddings.embed([embedding_text])

            self._vector_store.ensure_collection(JOBS_COLLECTION, len(vector))
            # Required for MatchingService's equals/lte filters on these fields (see
            # application/matching/service.py) — Qdrant Cloud runs in strict mode and rejects
            # filters on unindexed payload fields with a 400.
            self._vector_store.ensure_payload_index(JOBS_COLLECTION, "lifecycle_status", "keyword")
            self._vector_store.ensure_payload_index(
                JOBS_COLLECTION, "min_experience_years", "float"
            )
            self._vector_store.upsert(
                JOBS_COLLECTION,
                str(job.id),
                vector,
                payload={
                    "job_id": str(job.id),
                    "company_id": str(job.company_id),
                    "required_skills": job.required_skills,
                    "min_experience_years": job.min_experience_years,
                    "work_mode": job.work_mode.value if job.work_mode else None,
                    "salary_min": job.salary_min,
                    "salary_max": job.salary_max,
                    "location_country": job.location.country,
                    "lifecycle_status": job.lifecycle_status.value,
                },
            )

            job.processing_status = JobProcessingStatus.READY
            job.error_message = None
            self._jobs.update(job)

            self._matching_dispatcher.dispatch_compute_for_job(job.id)
        except Exception as exc:
            job.processing_status = JobProcessingStatus.FAILED
            job.error_message = str(exc)[:500]
            self._jobs.update(job)
            raise
