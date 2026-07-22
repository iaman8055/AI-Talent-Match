from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import (
    get_agent_config_service,
    get_candidate_repository,
    get_job_repository,
    require_roles,
)
from src.api.v1.agent.schemas import (
    AgentConfigResponse,
    AgentDecisionResponse,
    UpdateAgentConfigRequest,
)
from src.application.agent.service import AgentConfigService
from src.domain.candidate.entities import Candidate
from src.domain.candidate.repository import CandidateRepository
from src.domain.job.repository import JobRepository
from src.domain.user.entities import User, UserRole

router = APIRouter(prefix="/candidates/me", tags=["agent"])


def _require_candidate(current_user: User, candidate_repo: CandidateRepository) -> Candidate:
    candidate = candidate_repo.get_by_user_id(current_user.id)
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate profile not found")
    return candidate


@router.get("/agent-config", response_model=AgentConfigResponse)
def get_agent_config(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    agent_config_service: AgentConfigService = Depends(get_agent_config_service),
) -> AgentConfigResponse:
    candidate = _require_candidate(current_user, candidate_repo)
    config = agent_config_service.get_or_create(candidate.id)
    return AgentConfigResponse.from_entity(config)


@router.put("/agent-config", response_model=AgentConfigResponse)
def update_agent_config(
    body: UpdateAgentConfigRequest,
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    agent_config_service: AgentConfigService = Depends(get_agent_config_service),
) -> AgentConfigResponse:
    candidate = _require_candidate(current_user, candidate_repo)
    updates = body.model_dump(exclude_unset=True)
    config = agent_config_service.update(candidate.id, updates)
    return AgentConfigResponse.from_entity(config)


@router.get("/agent-decisions", response_model=list[AgentDecisionResponse])
def list_agent_decisions(
    current_user: User = Depends(require_roles(UserRole.CANDIDATE)),
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    agent_config_service: AgentConfigService = Depends(get_agent_config_service),
) -> list[AgentDecisionResponse]:
    candidate = _require_candidate(current_user, candidate_repo)
    result = []
    for decision in agent_config_service.list_decisions(candidate.id):
        job = job_repo.get_by_id(decision.job_id)
        if job is not None:
            result.append(AgentDecisionResponse.from_entity(decision, job.title))
    return result
