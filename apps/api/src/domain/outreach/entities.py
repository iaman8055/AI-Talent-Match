import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class OutreachDraftStatus(StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    DISCARDED = "discarded"


@dataclass
class OutreachDraft:
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    match_score_id: uuid.UUID | None
    candidate_summary: str
    subject: str
    body: str
    status: OutreachDraftStatus
    sent_by_user_id: uuid.UUID | None
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime
