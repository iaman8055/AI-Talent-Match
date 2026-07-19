import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ApplicationStatus(StrEnum):
    SOURCED = "sourced"
    INVITED = "invited"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"


@dataclass
class Application:
    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: ApplicationStatus
    invited_by_user_id: uuid.UUID | None
    applied_at: datetime | None
    status_updated_at: datetime
    created_at: datetime
    updated_at: datetime
