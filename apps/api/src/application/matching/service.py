import uuid
from datetime import UTC, datetime

from src.application.ai.ports import RerankCandidate, RerankerClient, VectorFilter, VectorStore
from src.application.matching.ports import RecruiterAgentDispatcher
from src.application.matching.scoring import (
    MATCHER_VERSION,
    compose_overall_score,
    experience_fit_score,
    location_fit_score,
    salary_fit_score,
    semantic_score,
    skill_overlap_score,
)
from src.domain.candidate.entities import Candidate, ResumeStatus
from src.domain.candidate.repository import CandidateRepository, ResumeRepository
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import Job, JobLifecycleStatus, JobProcessingStatus
from src.domain.job.repository import JobRepository
from src.domain.matching.entities import MatchScore
from src.domain.matching.repository import MatchScoreRepository

CANDIDATES_COLLECTION = "candidates"
JOBS_COLLECTION = "jobs"
SEARCH_LIMIT = 100
RERANK_LIMIT = 50
DEFAULT_MATCH_THRESHOLD = 70


def _candidate_text(candidate: Candidate) -> str:
    parts = [
        candidate.headline or "",
        candidate.summary or "",
        f"Skills: {', '.join(candidate.skills)}" if candidate.skills else "",
        (
            f"Experience: {candidate.total_experience_years} years"
            if candidate.total_experience_years is not None
            else ""
        ),
    ]
    return "\n".join(part for part in parts if part)


def _job_text(job: Job) -> str:
    parts = [
        job.title,
        job.summary or "",
        f"Required skills: {', '.join(job.required_skills)}" if job.required_skills else "",
        f"Responsibilities: {'; '.join(job.responsibilities)}" if job.responsibilities else "",
    ]
    return "\n".join(part for part in parts if part)


class MatchingService:
    """Invoked from Celery tasks (infrastructure/tasks/matching_tasks.py), never from a
    request-handling code path — matches the architecture doc's async-AI-pipeline rule. The two
    read methods (get_job_candidates/get_recommended_jobs) are the only parts of this service
    safe to call synchronously, since they only read already-computed match_scores rows."""

    def __init__(
        self,
        candidate_repo: CandidateRepository,
        resume_repo: ResumeRepository,
        job_repo: JobRepository,
        company_repo: CompanyRepository,
        match_score_repo: MatchScoreRepository,
        vector_store: VectorStore,
        reranker: RerankerClient,
        recruiter_agent_dispatcher: RecruiterAgentDispatcher,
    ) -> None:
        self._candidates = candidate_repo
        self._resumes = resume_repo
        self._jobs = job_repo
        self._companies = company_repo
        self._match_scores = match_score_repo
        self._vector_store = vector_store
        self._reranker = reranker
        self._recruiter_agent_dispatcher = recruiter_agent_dispatcher

    def _latest_resume_content_hash(self, candidate_id: uuid.UUID) -> str:
        resumes = self._resumes.list_by_candidate(candidate_id)
        if not resumes:
            return ""
        ready = [r for r in resumes if r.status == ResumeStatus.READY]
        pool = ready or resumes
        return max(pool, key=lambda r: r.version).content_hash

    def compute_matches_for_job(self, job_id: uuid.UUID) -> None:
        job = self._jobs.get_by_id(job_id)
        if job is None or job.processing_status != JobProcessingStatus.READY:
            return

        job_vector = self._vector_store.get_vector(JOBS_COLLECTION, str(job.id))
        if job_vector is None:
            return

        query_filter = None
        if job.min_experience_years is not None and job.min_experience_years > 0:
            query_filter = VectorFilter(gte={"total_experience_years": job.min_experience_years})

        hits = self._vector_store.search(
            CANDIDATES_COLLECTION, job_vector, SEARCH_LIMIT, query_filter
        )
        if not hits:
            return

        candidates_by_id: dict[str, Candidate] = {}
        for hit in hits[:RERANK_LIMIT]:
            candidate = self._candidates.get_by_id(uuid.UUID(hit.point_id))
            if candidate is not None:
                candidates_by_id[hit.point_id] = candidate

        job_hash = job.content_hash
        semantic_by_id = {hit.point_id: hit.score for hit in hits}
        pending: list[tuple[str, Candidate, str]] = []
        for point_id, candidate in candidates_by_id.items():
            candidate_hash = self._latest_resume_content_hash(candidate.id)
            existing = self._match_scores.get_latest_for_pair(candidate.id, job.id, MATCHER_VERSION)
            if (
                existing is not None
                and existing.candidate_content_hash == candidate_hash
                and existing.job_content_hash == job_hash
            ):
                continue
            pending.append((point_id, candidate, candidate_hash))

        if not pending:
            return

        rerank_candidates = [
            RerankCandidate(id=point_id, text=_candidate_text(candidate))
            for point_id, candidate, _ in pending
        ]
        rerank_by_id = {
            r.id: r.score for r in self._reranker.rerank(_job_text(job), rerank_candidates)
        }

        for point_id, candidate, candidate_hash in pending:
            self._persist_score(
                candidate=candidate,
                job=job,
                semantic_similarity=semantic_by_id[point_id],
                rerank_value=rerank_by_id.get(point_id, 0.0),
                candidate_hash=candidate_hash,
                job_hash=job_hash,
            )

    def compute_matches_for_candidate(self, candidate_id: uuid.UUID) -> None:
        candidate = self._candidates.get_by_id(candidate_id)
        if candidate is None:
            return

        candidate_vector = self._vector_store.get_vector(CANDIDATES_COLLECTION, str(candidate.id))
        if candidate_vector is None:
            return

        query_filter = VectorFilter(equals={"lifecycle_status": JobLifecycleStatus.PUBLISHED.value})
        if candidate.total_experience_years is not None:
            query_filter.lte = {"min_experience_years": candidate.total_experience_years}

        hits = self._vector_store.search(
            JOBS_COLLECTION, candidate_vector, SEARCH_LIMIT, query_filter
        )
        if not hits:
            return

        jobs_by_id: dict[str, Job] = {}
        for hit in hits[:RERANK_LIMIT]:
            job = self._jobs.get_by_id(uuid.UUID(hit.point_id))
            if (
                job is not None
                and job.processing_status == JobProcessingStatus.READY
                and job.lifecycle_status == JobLifecycleStatus.PUBLISHED
            ):
                jobs_by_id[hit.point_id] = job

        candidate_hash = self._latest_resume_content_hash(candidate.id)
        semantic_by_id = {hit.point_id: hit.score for hit in hits}
        pending: list[tuple[str, Job]] = []
        for point_id, job in jobs_by_id.items():
            existing = self._match_scores.get_latest_for_pair(candidate.id, job.id, MATCHER_VERSION)
            if (
                existing is not None
                and existing.candidate_content_hash == candidate_hash
                and existing.job_content_hash == job.content_hash
            ):
                continue
            pending.append((point_id, job))

        if not pending:
            return

        rerank_candidates = [
            RerankCandidate(id=point_id, text=_job_text(job)) for point_id, job in pending
        ]
        rerank_by_id = {
            r.id: r.score
            for r in self._reranker.rerank(_candidate_text(candidate), rerank_candidates)
        }

        for point_id, job in pending:
            self._persist_score(
                candidate=candidate,
                job=job,
                semantic_similarity=semantic_by_id[point_id],
                rerank_value=rerank_by_id.get(point_id, 0.0),
                candidate_hash=candidate_hash,
                job_hash=job.content_hash,
            )

        # Fresh scores exist now — this is exactly the trigger point for the Recruiter Agent
        # (docs/03-ROADMAP.md Phase 7): it reads match_scores, so it must never run before this.
        self._recruiter_agent_dispatcher.dispatch_for_candidate(candidate.id)

    def _persist_score(
        self,
        *,
        candidate: Candidate,
        job: Job,
        semantic_similarity: float,
        rerank_value: float,
        candidate_hash: str,
        job_hash: str,
    ) -> None:
        sem_score = semantic_score(semantic_similarity)
        skill_score = skill_overlap_score(candidate.skills, job.required_skills)
        exp_score = experience_fit_score(candidate.total_experience_years, job.min_experience_years)
        sal_score = salary_fit_score(
            candidate.desired_salary_min,
            candidate.desired_salary_max,
            job.salary_min,
            job.salary_max,
        )
        loc_score = location_fit_score(
            job.work_mode, candidate.location.country, job.location.country
        )

        overall = compose_overall_score(
            semantic=sem_score,
            rerank=rerank_value,
            skill_overlap=skill_score,
            experience_fit=exp_score,
            salary_fit=sal_score,
            location_fit=loc_score,
        )

        self._match_scores.add(
            MatchScore(
                id=uuid.uuid4(),
                candidate_id=candidate.id,
                job_id=job.id,
                overall_score=overall,
                semantic_score=sem_score,
                skill_overlap_score=skill_score,
                experience_fit_score=exp_score,
                salary_fit_score=sal_score,
                location_fit_score=loc_score,
                rerank_score=rerank_value,
                matcher_version=MATCHER_VERSION,
                candidate_content_hash=candidate_hash,
                job_content_hash=job_hash,
                computed_at=datetime.now(UTC),
            )
        )

    def get_job_candidates(self, job_id: uuid.UUID, threshold: float) -> list[MatchScore]:
        scores = self._match_scores.list_latest_for_job(job_id)
        above = [s for s in scores if s.overall_score >= threshold]
        return sorted(above, key=lambda s: s.overall_score, reverse=True)

    def get_recommended_jobs(self, candidate_id: uuid.UUID) -> list[MatchScore]:
        scores = self._match_scores.list_latest_for_candidate(candidate_id)
        result = []
        for score in scores:
            job = self._jobs.get_by_id(score.job_id)
            if job is None or job.lifecycle_status != JobLifecycleStatus.PUBLISHED:
                continue
            company = self._companies.get_by_id(job.company_id)
            threshold = company.match_threshold if company is not None else DEFAULT_MATCH_THRESHOLD
            if score.overall_score >= threshold:
                result.append(score)
        return sorted(result, key=lambda s: s.overall_score, reverse=True)
