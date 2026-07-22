from fastapi import APIRouter, Depends

from src.api.deps import (
    get_candidate_repository,
    get_company_repository,
    get_job_repository,
    get_matching_service,
    get_outreach_draft_repository,
    require_job_membership,
    require_roles,
)
from src.api.v1.candidates.schemas import CandidateResponse
from src.api.v1.jobs.schemas import JobResponse
from src.api.v1.matching.schemas import (
    JobCandidateMatchResponse,
    MatchScoreDetail,
    RecommendedJobResponse,
)
from src.application.company.service import DEFAULT_MATCH_THRESHOLD
from src.application.matching.service import MatchingService
from src.domain.candidate.repository import CandidateRepository
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import Job
from src.domain.job.repository import JobRepository
from src.domain.outreach.entities import OutreachDraftStatus
from src.domain.outreach.repository import OutreachDraftRepository
from src.domain.user.entities import User, UserRole

router = APIRouter(tags=["matching"])


@router.get("/jobs/{job_id}/candidates", response_model=list[JobCandidateMatchResponse])
def list_job_candidates(
    job: Job = Depends(require_job_membership()),
    company_repo: CompanyRepository = Depends(get_company_repository),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    outreach_draft_repo: OutreachDraftRepository = Depends(get_outreach_draft_repository),
    matching_service: MatchingService = Depends(get_matching_service),
) -> list[JobCandidateMatchResponse]:
    company = company_repo.get_by_id(job.company_id)
    threshold = company.match_threshold if company is not None else DEFAULT_MATCH_THRESHOLD
    scores = matching_service.get_job_candidates(job.id, threshold)

    pending_candidate_ids = {
        draft.candidate_id
        for draft in outreach_draft_repo.list_by_job(job.id)
        if draft.status == OutreachDraftStatus.DRAFT
    }

    results: list[JobCandidateMatchResponse] = []
    for score in scores:
        candidate = candidate_repo.get_by_id(score.candidate_id)
        if candidate is None:
            continue
        results.append(
            JobCandidateMatchResponse(
                candidate=CandidateResponse.from_entity(candidate),
                match=MatchScoreDetail.from_entity(score),
                has_pending_outreach_draft=candidate.id in pending_candidate_ids,
            )
        )
    return results


@router.get("/candidates/me/recommended-jobs", response_model=list[RecommendedJobResponse])
def list_recommended_jobs(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    matching_service: MatchingService = Depends(get_matching_service),
) -> list[RecommendedJobResponse]:
    candidate = candidate_repo.get_by_user_id(current_user.id)
    if candidate is None:
        return []
    scores = matching_service.get_recommended_jobs(candidate.id)

    results: list[RecommendedJobResponse] = []
    for score in scores:
        job = job_repo.get_by_id(score.job_id)
        if job is None:
            continue
        results.append(
            RecommendedJobResponse(
                job=JobResponse.from_entity(job), match=MatchScoreDetail.from_entity(score)
            )
        )
    return results
