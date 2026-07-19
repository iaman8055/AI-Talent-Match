import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import (
    get_application_repository,
    get_application_service,
    get_candidate_repository,
    get_current_user,
    get_job_repository,
    get_match_score_repository,
    require_application_membership,
    require_job_membership,
    require_roles,
)
from src.api.v1.applications.schemas import (
    ApplicationResponse,
    ApplyToJobRequest,
    CandidateApplicationResponse,
    CandidateDetailResponse,
    InviteCandidateRequest,
)
from src.api.v1.candidates.schemas import CandidateResponse
from src.api.v1.jobs.schemas import JobResponse
from src.api.v1.matching.schemas import MatchScoreDetail
from src.application.applications.service import ApplicationService
from src.application.matching.scoring import MATCHER_VERSION, matched_and_missing_skills
from src.domain.applications.entities import Application
from src.domain.applications.repository import ApplicationRepository
from src.domain.candidate.repository import CandidateRepository
from src.domain.job.entities import Job
from src.domain.job.repository import JobRepository
from src.domain.matching.repository import MatchScoreRepository
from src.domain.user.entities import User, UserRole

router = APIRouter(tags=["applications"])


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}",
    response_model=CandidateDetailResponse,
)
def get_candidate_detail(
    candidate_id: uuid.UUID,
    job: Job = Depends(require_job_membership()),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    match_score_repo: MatchScoreRepository = Depends(get_match_score_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
) -> CandidateDetailResponse:
    candidate = candidate_repo.get_by_id(candidate_id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found")

    match = match_score_repo.get_latest_for_pair(candidate.id, job.id, MATCHER_VERSION)
    application = application_repo.get_by_job_and_candidate(job.id, candidate.id)
    matched_skills, missing_skills = matched_and_missing_skills(
        candidate.skills, job.required_skills
    )

    return CandidateDetailResponse(
        candidate=CandidateResponse.from_entity(candidate),
        match=MatchScoreDetail.from_entity(match) if match else None,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        application=ApplicationResponse.from_entity(application) if application else None,
    )


@router.post(
    "/jobs/{job_id}/invite",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def invite_candidate(
    body: InviteCandidateRequest,
    job: Job = Depends(require_job_membership()),
    current_user: User = Depends(get_current_user),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    application = application_service.invite_candidate(job, body.candidate_id, current_user.id)
    return ApplicationResponse.from_entity(application)


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationResponse])
def list_job_applications(
    job: Job = Depends(require_job_membership()),
    application_repo: ApplicationRepository = Depends(get_application_repository),
) -> list[ApplicationResponse]:
    applications = application_repo.list_by_job(job.id)
    return [ApplicationResponse.from_entity(a) for a in applications]


@router.post(
    "/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED
)
def apply_to_job(
    body: ApplyToJobRequest,
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    candidate = candidate_repo.get_by_user_id(current_user.id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate profile not found")
    application = application_service.apply_to_job(candidate.id, body.job_id)
    return ApplicationResponse.from_entity(application)


@router.get("/applications", response_model=list[CandidateApplicationResponse])
def list_my_applications(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    application_repo: ApplicationRepository = Depends(get_application_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> list[CandidateApplicationResponse]:
    candidate = candidate_repo.get_by_user_id(current_user.id)
    if candidate is None:
        return []

    result = []
    for application in application_repo.list_by_candidate(candidate.id):
        job = job_repo.get_by_id(application.job_id)
        if job is not None:
            result.append(
                CandidateApplicationResponse(
                    application=ApplicationResponse.from_entity(application),
                    job=JobResponse.from_entity(job),
                )
            )
    return result


@router.post("/applications/{application_id}/screen", response_model=ApplicationResponse)
def screen_application(
    application: Application = Depends(require_application_membership()),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    return ApplicationResponse.from_entity(application_service.screen_application(application))


@router.post("/applications/{application_id}/interview", response_model=ApplicationResponse)
def interview_application(
    application: Application = Depends(require_application_membership()),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    return ApplicationResponse.from_entity(application_service.interview_application(application))


@router.post("/applications/{application_id}/offer", response_model=ApplicationResponse)
def offer_application(
    application: Application = Depends(require_application_membership()),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    return ApplicationResponse.from_entity(application_service.offer_application(application))


@router.post("/applications/{application_id}/reject", response_model=ApplicationResponse)
def reject_application(
    application: Application = Depends(require_application_membership()),
    application_service: ApplicationService = Depends(get_application_service),
) -> ApplicationResponse:
    return ApplicationResponse.from_entity(application_service.reject_application(application))
