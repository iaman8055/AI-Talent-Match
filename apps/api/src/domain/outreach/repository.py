import uuid
from typing import Protocol

from src.domain.outreach.entities import OutreachDraft


class OutreachDraftRepository(Protocol):
    def get_by_id(self, draft_id: uuid.UUID) -> OutreachDraft | None: ...

    def exists_for_pair(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> bool:
        """True once a draft has ever been generated for this pair — keeps a resume re-parse or
        a retried Celery task from generating a duplicate outreach message."""
        ...

    def list_by_job(self, job_id: uuid.UUID) -> list[OutreachDraft]: ...

    def list_by_jobs(self, job_ids: list[uuid.UUID]) -> list[OutreachDraft]:
        """Bulk variant of list_by_job — backs the recruiter's cross-job outreach inbox without
        one query per job."""
        ...

    def list_by_candidate(self, candidate_id: uuid.UUID) -> list[OutreachDraft]: ...

    def add(self, draft: OutreachDraft) -> OutreachDraft: ...

    def update(self, draft: OutreachDraft) -> OutreachDraft: ...
