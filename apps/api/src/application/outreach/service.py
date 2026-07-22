import uuid
from datetime import UTC, datetime

from src.application.auth.ports import EmailSender
from src.application.exceptions import ConflictError, NotFoundError
from src.domain.candidate.repository import CandidateRepository
from src.domain.company.repository import CompanyRepository
from src.domain.job.repository import JobRepository
from src.domain.outreach.entities import OutreachDraft, OutreachDraftStatus
from src.domain.outreach.repository import OutreachDraftRepository
from src.domain.user.repository import UserRepository


class OutreachDraftService:
    """Synchronous, request-path service backing `/outreach-drafts` — no LLM calls here, those
    only ever happen in `agents/recruiter_agent/graph.py`, invoked from Celery."""

    def __init__(
        self,
        draft_repo: OutreachDraftRepository,
        job_repo: JobRepository,
        company_repo: CompanyRepository,
        candidate_repo: CandidateRepository,
        user_repo: UserRepository,
        email_sender: EmailSender,
    ) -> None:
        self._drafts = draft_repo
        self._jobs = job_repo
        self._companies = company_repo
        self._candidates = candidate_repo
        self._users = user_repo
        self._email_sender = email_sender

    def list_for_company_user(
        self, user_id: uuid.UUID, job_id: uuid.UUID | None = None
    ) -> list[OutreachDraft]:
        companies = self._companies.list_for_user(user_id)
        job_ids = [
            job.id for company in companies for job in self._jobs.list_by_company(company.id)
        ]
        if job_id is not None:
            job_ids = [j for j in job_ids if j == job_id]
        drafts = self._drafts.list_by_jobs(job_ids)
        return sorted(drafts, key=lambda d: d.created_at, reverse=True)

    def _get_draft(self, draft_id: uuid.UUID) -> OutreachDraft:
        draft = self._drafts.get_by_id(draft_id)
        if draft is None:
            raise NotFoundError("Outreach draft not found")
        return draft

    def update_draft(self, draft_id: uuid.UUID, updates: dict[str, object]) -> OutreachDraft:
        draft = self._get_draft(draft_id)
        if draft.status != OutreachDraftStatus.DRAFT:
            raise ConflictError("Only a pending draft can be edited")
        for field_name, value in updates.items():
            setattr(draft, field_name, value)
        draft.updated_at = datetime.now(UTC)
        return self._drafts.update(draft)

    def send(self, draft_id: uuid.UUID, sent_by_user_id: uuid.UUID) -> OutreachDraft:
        draft = self._get_draft(draft_id)
        if draft.status != OutreachDraftStatus.DRAFT:
            raise ConflictError("Only a pending draft can be sent")

        candidate = self._candidates.get_by_id(draft.candidate_id)
        candidate_user = self._users.get_by_id(candidate.user_id) if candidate else None
        if candidate_user is not None:
            self._email_sender.send_outreach_email(candidate_user, draft.subject, draft.body)

        now = datetime.now(UTC)
        draft.status = OutreachDraftStatus.SENT
        draft.sent_by_user_id = sent_by_user_id
        draft.sent_at = now
        draft.updated_at = now
        return self._drafts.update(draft)

    def discard(self, draft_id: uuid.UUID) -> OutreachDraft:
        draft = self._get_draft(draft_id)
        if draft.status != OutreachDraftStatus.DRAFT:
            raise ConflictError("Only a pending draft can be discarded")
        draft.status = OutreachDraftStatus.DISCARDED
        draft.updated_at = datetime.now(UTC)
        return self._drafts.update(draft)
