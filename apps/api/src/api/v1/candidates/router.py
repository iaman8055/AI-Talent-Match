import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from src.api.deps import get_candidate_service, require_roles
from src.api.v1.candidates.schemas import (
    CandidateResponse,
    DownloadUrlResponse,
    ResumeResponse,
    UpdateProfileRequest,
)
from src.application.candidate.service import MAX_RESUME_FILE_SIZE_BYTES, CandidateService
from src.domain.candidate.entities import Location, WorkMode
from src.domain.user.entities import User, UserRole

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/me", response_model=CandidateResponse)
def get_my_profile(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> CandidateResponse:
    candidate = candidate_service.get_or_create_profile(current_user.id)
    return CandidateResponse.from_entity(candidate)


@router.patch("/me/profile", response_model=CandidateResponse)
def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> CandidateResponse:
    updates: dict[str, object] = {}
    for field_name, value in body.model_dump(exclude_unset=True).items():
        if field_name == "location":
            updates["location"] = Location(**value) if value is not None else Location()
        elif field_name == "work_mode_preference":
            updates["work_mode_preference"] = WorkMode(value) if value is not None else None
        else:
            updates[field_name] = value

    candidate = candidate_service.update_profile(current_user.id, updates)
    return CandidateResponse.from_entity(candidate)


@router.post("/me/resume", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> ResumeResponse:
    # Bounded read, not file.read(): reading the whole body first and only checking the size
    # afterwards would let an oversized upload sit fully buffered in memory before being
    # rejected — a DoS vector distinct from (and cheaper to fix than) the service-layer size
    # check on the already-read bytes.
    file_bytes = await file.read(MAX_RESUME_FILE_SIZE_BYTES + 1)
    if len(file_bytes) > MAX_RESUME_FILE_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Resume file exceeds the 5MB size limit"
        )
    resume = candidate_service.upload_resume(current_user.id, file.filename or "resume", file_bytes)
    return ResumeResponse.from_entity(resume)


@router.get("/me/resume", response_model=list[ResumeResponse])
def list_resumes(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> list[ResumeResponse]:
    resumes = candidate_service.list_resumes(current_user.id)
    return [ResumeResponse.from_entity(resume) for resume in resumes]


@router.get("/me/resume/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> ResumeResponse:
    resume = candidate_service.get_resume(current_user.id, resume_id)
    return ResumeResponse.from_entity(resume)


@router.get("/me/resume/{resume_id}/download-url", response_model=DownloadUrlResponse)
def get_resume_download_url(
    resume_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_service: CandidateService = Depends(get_candidate_service),
) -> DownloadUrlResponse:
    url = candidate_service.get_resume_download_url(current_user.id, resume_id)
    return DownloadUrlResponse(url=url)
