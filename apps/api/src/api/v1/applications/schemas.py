import uuid
from datetime import datetime

from pydantic import BaseModel

from src.api.v1.candidates.schemas import CandidateResponse
from src.api.v1.jobs.schemas import JobResponse
from src.api.v1.matching.schemas import MatchScoreDetail
from src.domain.applications.entities import Application, ApplicationStatus


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: ApplicationStatus
    invited_by_user_id: uuid.UUID | None
    applied_at: datetime | None
    status_updated_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, application: Application) -> "ApplicationResponse":
        return cls(
            id=application.id,
            job_id=application.job_id,
            candidate_id=application.candidate_id,
            status=application.status,
            invited_by_user_id=application.invited_by_user_id,
            applied_at=application.applied_at,
            status_updated_at=application.status_updated_at,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


class InviteCandidateRequest(BaseModel):
    candidate_id: uuid.UUID


class ApplyToJobRequest(BaseModel):
    job_id: uuid.UUID


class CandidateDetailResponse(BaseModel):
    candidate: CandidateResponse
    match: MatchScoreDetail | None
    matched_skills: list[str]
    missing_skills: list[str]
    application: ApplicationResponse | None


class CandidateApplicationResponse(BaseModel):
    application: ApplicationResponse
    job: JobResponse
