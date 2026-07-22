import uuid

from fastapi import APIRouter, Depends, Query

from src.api.deps import (
    get_candidate_repository,
    get_current_user,
    get_job_repository,
    get_outreach_draft_service,
    require_outreach_draft_membership,
)
from src.api.v1.outreach.schemas import OutreachDraftResponse, UpdateOutreachDraftRequest
from src.application.outreach.service import OutreachDraftService
from src.domain.candidate.repository import CandidateRepository
from src.domain.job.repository import JobRepository
from src.domain.outreach.entities import OutreachDraft
from src.domain.user.entities import User

router = APIRouter(prefix="/outreach-drafts", tags=["outreach"])


def _to_response(
    draft: OutreachDraft, candidate_repo: CandidateRepository, job_repo: JobRepository
) -> OutreachDraftResponse | None:
    candidate = candidate_repo.get_by_id(draft.candidate_id)
    job = job_repo.get_by_id(draft.job_id)
    if candidate is None or job is None:
        return None
    return OutreachDraftResponse.from_entity(
        draft, candidate.full_name or "Unnamed candidate", job.title
    )


@router.get("", response_model=list[OutreachDraftResponse])
def list_outreach_drafts(
    job_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    outreach_service: OutreachDraftService = Depends(get_outreach_draft_service),
) -> list[OutreachDraftResponse]:
    drafts = outreach_service.list_for_company_user(current_user.id, job_id)
    responses = [_to_response(draft, candidate_repo, job_repo) for draft in drafts]
    return [response for response in responses if response is not None]


@router.patch("/{draft_id}", response_model=OutreachDraftResponse)
def update_outreach_draft(
    body: UpdateOutreachDraftRequest,
    draft: OutreachDraft = Depends(require_outreach_draft_membership()),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    outreach_service: OutreachDraftService = Depends(get_outreach_draft_service),
) -> OutreachDraftResponse:
    updates = body.model_dump(exclude_unset=True)
    updated = outreach_service.update_draft(draft.id, updates)
    response = _to_response(updated, candidate_repo, job_repo)
    assert response is not None  # candidate/job existed for the membership check above
    return response


@router.post("/{draft_id}/send", response_model=OutreachDraftResponse)
def send_outreach_draft(
    draft: OutreachDraft = Depends(require_outreach_draft_membership()),
    current_user: User = Depends(get_current_user),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    outreach_service: OutreachDraftService = Depends(get_outreach_draft_service),
) -> OutreachDraftResponse:
    sent = outreach_service.send(draft.id, current_user.id)
    response = _to_response(sent, candidate_repo, job_repo)
    assert response is not None
    return response


@router.post("/{draft_id}/discard", response_model=OutreachDraftResponse)
def discard_outreach_draft(
    draft: OutreachDraft = Depends(require_outreach_draft_membership()),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    outreach_service: OutreachDraftService = Depends(get_outreach_draft_service),
) -> OutreachDraftResponse:
    discarded = outreach_service.discard(draft.id)
    response = _to_response(discarded, candidate_repo, job_repo)
    assert response is not None
    return response
