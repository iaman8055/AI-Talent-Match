import uuid
from datetime import UTC, datetime
from datetime import date as date_cls

from src.application.ai.ports import EmbeddingClient, LLMClient, VectorStore
from src.application.candidate.extraction_schema import (
    RESUME_EXTRACTION_INSTRUCTIONS,
    ResumeExtractionResult,
)
from src.application.candidate.ports import StorageClient, TextExtractor
from src.application.matching.ports import MatchingDispatcher
from src.domain.candidate.entities import (
    Candidate,
    Education,
    Location,
    ResumeStatus,
    WorkExperience,
)
from src.domain.candidate.repository import CandidateRepository, ResumeRepository

CANDIDATES_COLLECTION = "candidates"
EMBEDDING_VECTOR_SIZE = 1024  # bge-m3
_MAX_TEXT_CHARS = 8000


def _parse_partial_date(value: str | None) -> date_cls | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _clean_resume_text(text: str) -> str:
    # Collapse blank lines/whitespace and cap at a sane token budget (architecture doc §7.4)
    # before this text goes anywhere near the LLM.
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line)
    return cleaned[:_MAX_TEXT_CHARS]


def _build_embedding_text(candidate: Candidate) -> str:
    parts = [candidate.headline or "", candidate.summary or "", ", ".join(candidate.skills)]
    return "\n".join(part for part in parts if part)[:_MAX_TEXT_CHARS]


class ResumeParsingService:
    """Invoked from Celery tasks (infrastructure/tasks/resume_tasks.py), never from a
    request-handling code path — matches the architecture doc's async-AI-pipeline rule."""

    def __init__(
        self,
        candidate_repo: CandidateRepository,
        resume_repo: ResumeRepository,
        storage: StorageClient,
        text_extractor: TextExtractor,
        llm_client: LLMClient,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        matching_dispatcher: MatchingDispatcher,
    ) -> None:
        self._candidates = candidate_repo
        self._resumes = resume_repo
        self._storage = storage
        self._text_extractor = text_extractor
        self._llm = llm_client
        self._embeddings = embedding_client
        self._vector_store = vector_store
        self._matching_dispatcher = matching_dispatcher

    def parse_resume(self, resume_id: uuid.UUID) -> None:
        resume = self._resumes.get_by_id(resume_id)
        if resume is None:
            return

        resume.status = ResumeStatus.PARSING
        self._resumes.update(resume)

        try:
            file_bytes = self._storage.download(resume.s3_key)
            text = self._text_extractor.extract_text(file_bytes, resume.file_type)
            cleaned_text = _clean_resume_text(text)

            result = self._llm.extract_structured(
                RESUME_EXTRACTION_INSTRUCTIONS, cleaned_text, ResumeExtractionResult
            )

            candidate = self._candidates.get_by_id(resume.candidate_id)
            if candidate is None:
                raise ValueError(f"Candidate {resume.candidate_id} not found")

            self._apply_extraction(candidate, result)
            self._candidates.update(candidate)

            resume.status = ResumeStatus.PARSED
            resume.parsed_at = datetime.now(UTC)
            resume.error_message = None
            self._resumes.update(resume)
        except Exception as exc:
            resume.status = ResumeStatus.FAILED
            resume.error_message = str(exc)[:500]
            self._resumes.update(resume)
            raise

    def embed_resume(self, resume_id: uuid.UUID) -> None:
        resume = self._resumes.get_by_id(resume_id)
        if resume is None:
            return

        resume.status = ResumeStatus.EMBEDDING
        self._resumes.update(resume)

        try:
            candidate = self._candidates.get_by_id(resume.candidate_id)
            if candidate is None:
                raise ValueError(f"Candidate {resume.candidate_id} not found")

            embedding_text = _build_embedding_text(candidate)
            [vector] = self._embeddings.embed([embedding_text])

            self._vector_store.ensure_collection(CANDIDATES_COLLECTION, EMBEDDING_VECTOR_SIZE)
            self._vector_store.upsert(
                CANDIDATES_COLLECTION,
                str(candidate.id),
                vector,
                payload={
                    "candidate_id": str(candidate.id),
                    "resume_id": str(resume.id),
                    "skills": candidate.skills,
                    "total_experience_years": candidate.total_experience_years,
                    "location_country": candidate.location.country,
                    "work_mode_preference": (
                        candidate.work_mode_preference.value
                        if candidate.work_mode_preference
                        else None
                    ),
                },
            )

            resume.status = ResumeStatus.READY
            resume.error_message = None
            self._resumes.update(resume)

            self._matching_dispatcher.dispatch_compute_for_candidate(candidate.id)
        except Exception as exc:
            resume.status = ResumeStatus.FAILED
            resume.error_message = str(exc)[:500]
            self._resumes.update(resume)
            raise

    def _apply_extraction(self, candidate: Candidate, result: ResumeExtractionResult) -> None:
        if result.full_name:
            candidate.full_name = result.full_name
        if result.headline:
            candidate.headline = result.headline
        if result.summary:
            candidate.summary = result.summary
        if result.skills:
            candidate.skills = result.skills
        if result.total_experience_years is not None:
            candidate.total_experience_years = result.total_experience_years
        if any([result.location.country, result.location.region, result.location.city]):
            candidate.location = Location(
                country=result.location.country,
                region=result.location.region,
                city=result.location.city,
            )
        if result.work_experience:
            candidate.work_experience = [
                WorkExperience(
                    company=item.company,
                    title=item.title,
                    start_date=_parse_partial_date(item.start_date),
                    end_date=_parse_partial_date(item.end_date),
                    description=item.description,
                )
                for item in result.work_experience
            ]
        if result.education:
            candidate.education = [
                Education(
                    institution=item.institution,
                    degree=item.degree,
                    field_of_study=item.field_of_study,
                    start_date=_parse_partial_date(item.start_date),
                    end_date=_parse_partial_date(item.end_date),
                )
                for item in result.education
            ]
        candidate.updated_at = datetime.now(UTC)
