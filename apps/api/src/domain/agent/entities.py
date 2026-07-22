import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from src.domain.job.entities import WorkMode


class AgentDecisionAction(StrEnum):
    APPLIED = "applied"
    SKIPPED = "skipped"


@dataclass
class AgentConfig:
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


@dataclass
class AgentDecision:
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    match_score_id: uuid.UUID | None
    action: AgentDecisionAction
    reason: str
    constraint_results: dict[str, object] = field(default_factory=dict)
    decided_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
