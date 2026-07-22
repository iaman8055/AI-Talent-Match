import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.agent.entities import AgentConfig, AgentDecision, AgentDecisionAction
from src.domain.job.entities import WorkMode


class AgentConfigResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    auto_apply_enabled: bool
    target_roles: list[str]
    target_skills: list[str]
    target_locations: list[str]
    work_modes: list[WorkMode]
    min_salary: int | None
    min_match_score: int
    daily_apply_cap: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, config: AgentConfig) -> "AgentConfigResponse":
        return cls(
            id=config.id,
            candidate_id=config.candidate_id,
            auto_apply_enabled=config.auto_apply_enabled,
            target_roles=config.target_roles,
            target_skills=config.target_skills,
            target_locations=config.target_locations,
            work_modes=config.work_modes,
            min_salary=config.min_salary,
            min_match_score=config.min_match_score,
            daily_apply_cap=config.daily_apply_cap,
            created_at=config.created_at,
            updated_at=config.updated_at,
        )


class UpdateAgentConfigRequest(BaseModel):
    auto_apply_enabled: bool | None = None
    target_roles: list[str] | None = None
    target_skills: list[str] | None = None
    target_locations: list[str] | None = None
    work_modes: list[WorkMode] | None = None
    min_salary: int | None = Field(default=None, ge=0)
    min_match_score: int | None = Field(default=None, ge=0, le=100)
    daily_apply_cap: int | None = Field(default=None, ge=1, le=100)


class AgentDecisionResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    job_title: str
    action: AgentDecisionAction
    reason: str
    decided_at: datetime

    @classmethod
    def from_entity(cls, decision: AgentDecision, job_title: str) -> "AgentDecisionResponse":
        return cls(
            id=decision.id,
            job_id=decision.job_id,
            job_title=job_title,
            action=decision.action,
            reason=decision.reason,
            decided_at=decision.decided_at,
        )
