import uuid
from datetime import datetime
from typing import Protocol

from src.domain.agent.entities import AgentConfig, AgentDecision


class AgentConfigRepository(Protocol):
    def get_by_candidate(self, candidate_id: uuid.UUID) -> AgentConfig | None: ...

    def list_auto_apply_enabled(self) -> list[AgentConfig]:
        """Candidates whose agent is turned on — the Celery Beat scan's fan-out source."""
        ...

    def add(self, config: AgentConfig) -> AgentConfig: ...

    def update(self, config: AgentConfig) -> AgentConfig: ...


class AgentDecisionRepository(Protocol):
    def add(self, decision: AgentDecision) -> AgentDecision: ...

    def exists_for_pair(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> bool:
        """True once a decision (applied or skipped) has ever been logged for this pair — the
        dedup that keeps a recurring scan from re-evaluating the same pair every tick."""
        ...

    def count_applied_since(self, candidate_id: uuid.UUID, since: datetime) -> int:
        """Backs the daily auto-apply cap check."""
        ...

    def list_by_candidate(self, candidate_id: uuid.UUID) -> list[AgentDecision]:
        """Newest first."""
        ...
