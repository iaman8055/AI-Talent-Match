import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.outreach.entities import OutreachDraft, OutreachDraftStatus


class OutreachDraftResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    job_id: uuid.UUID
    job_title: str
    candidate_summary: str
    subject: str
    body: str
    status: OutreachDraftStatus
    sent_at: datetime | None
    created_at: datetime

    @classmethod
    def from_entity(
        cls, draft: OutreachDraft, candidate_name: str, job_title: str
    ) -> "OutreachDraftResponse":
        return cls(
            id=draft.id,
            candidate_id=draft.candidate_id,
            candidate_name=candidate_name,
            job_id=draft.job_id,
            job_title=job_title,
            candidate_summary=draft.candidate_summary,
            subject=draft.subject,
            body=draft.body,
            status=draft.status,
            sent_at=draft.sent_at,
            created_at=draft.created_at,
        )


class UpdateOutreachDraftRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=4000)
