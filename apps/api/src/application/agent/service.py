import uuid
from datetime import UTC, datetime

from src.application.exceptions import ValidationError
from src.domain.agent.entities import AgentConfig, AgentDecision
from src.domain.agent.repository import AgentConfigRepository, AgentDecisionRepository


class AgentConfigService:
    """Backs the synchronous `/candidates/me/agent-*` endpoints. No graph/decision logic here —
    that lives in `agents/apply_agent/graph.py`, invoked from Celery, never from a request path."""

    def __init__(
        self,
        agent_config_repo: AgentConfigRepository,
        agent_decision_repo: AgentDecisionRepository,
    ) -> None:
        self._configs = agent_config_repo
        self._decisions = agent_decision_repo

    def get_or_create(self, candidate_id: uuid.UUID) -> AgentConfig:
        config = self._configs.get_by_candidate(candidate_id)
        if config is not None:
            return config

        now = datetime.now(UTC)
        config = AgentConfig(
            id=uuid.uuid4(),
            candidate_id=candidate_id,
            auto_apply_enabled=False,
            target_roles=[],
            target_skills=[],
            target_locations=[],
            work_modes=[],
            min_salary=None,
            min_match_score=70,
            daily_apply_cap=20,
            created_at=now,
            updated_at=now,
        )
        return self._configs.add(config)

    _UPDATE_FIELDS = frozenset(
        {
            "auto_apply_enabled",
            "target_roles",
            "target_skills",
            "target_locations",
            "work_modes",
            "min_salary",
            "min_match_score",
            "daily_apply_cap",
        }
    )

    def update(self, candidate_id: uuid.UUID, updates: dict[str, object]) -> AgentConfig:
        """`updates` should only contain keys the caller explicitly wants to change, already
        coerced to their domain types (e.g. `work_modes` as `list[WorkMode]`) — same contract as
        `CandidateService.update_profile`, where that coercion happens at the router layer."""
        config = self.get_or_create(candidate_id)

        unknown_fields = set(updates) - self._UPDATE_FIELDS
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise ValidationError(f"Unknown agent config field(s): {names}")

        for field_name, value in updates.items():
            setattr(config, field_name, value)
        config.updated_at = datetime.now(UTC)
        return self._configs.update(config)

    def list_decisions(self, candidate_id: uuid.UUID) -> list[AgentDecision]:
        return self._decisions.list_by_candidate(candidate_id)
