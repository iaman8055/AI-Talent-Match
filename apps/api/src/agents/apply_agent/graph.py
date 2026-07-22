"""The Apply Agent graph (docs/02-ARCHITECTURE.md §5): scans this candidate's already-computed
`match_scores` rows for jobs published in the scan window, validates them against the
candidate's configured preferences, and applies on their behalf when everything clears — logging
every decision, including skips, to `agent_decisions`.

No node here calls an LLM/embedding/reranker — the semantic-search/rerank work already happened
in Phase 4's matching pipeline when the job/candidate became READY (docs/02-ARCHITECTURE.md
§7.3: the agent reuses cached match_scores rather than recomputing them). Every node is plain
Python. `act` reuses `ApplicationService.apply_to_job` exactly as Phase 5 built it — this *is*
the "internal apply path reused from Phase 5" from docs/03-ROADMAP.md's Phase 6 entry.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.application.agent.constraints import evaluate_constraints
from src.application.agent.reasoning import build_reasoning
from src.application.applications.service import ApplicationService
from src.application.matching.scoring import MATCHER_VERSION
from src.domain.agent.entities import AgentDecision, AgentDecisionAction
from src.domain.agent.repository import AgentConfigRepository, AgentDecisionRepository
from src.domain.job.entities import JobLifecycleStatus
from src.domain.job.repository import JobRepository
from src.domain.matching.repository import MatchScoreRepository

SCAN_WINDOW_HOURS = 24


class _PendingMatch(TypedDict):
    job_id: str
    match_score_id: str
    overall_score: float


class _Decision(TypedDict):
    job_id: str
    match_score_id: str
    action: str
    reason: str
    constraint_results: dict[str, object]


class ApplyAgentState(TypedDict):
    candidate_id: str
    should_run: bool
    min_match_score: int
    daily_apply_cap: int
    pending: list[_PendingMatch]
    constraint_results: dict[str, dict[str, object]]  # job_id -> ConstraintResult.as_dict()
    plan: list[_Decision]  # decide's output, before act attempts the "apply" ones
    decisions: list[_Decision]  # final, post-act


@dataclass
class ApplyAgentDeps:
    """Built fresh per Celery task invocation — same one-session-per-task discipline as every
    other Celery task in this app (see infrastructure/tasks/matching_tasks.py)."""

    agent_config_repo: AgentConfigRepository
    agent_decision_repo: AgentDecisionRepository
    match_score_repo: MatchScoreRepository
    job_repo: JobRepository
    application_service: ApplicationService


def build_apply_agent_graph(deps: ApplyAgentDeps) -> StateGraph[ApplyAgentState]:
    def load_config(state: ApplyAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        config = deps.agent_config_repo.get_by_candidate(candidate_id)
        if config is None or not config.auto_apply_enabled:
            return {"should_run": False}
        return {
            "should_run": True,
            "min_match_score": config.min_match_score,
            "daily_apply_cap": config.daily_apply_cap,
        }

    def route_after_config(state: ApplyAgentState) -> str:
        return "load_pending_matches" if state["should_run"] else END

    def load_pending_matches(state: ApplyAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        window_start = datetime.now(UTC) - timedelta(hours=SCAN_WINDOW_HOURS)

        pending: list[_PendingMatch] = []
        for match in deps.match_score_repo.list_latest_for_candidate(candidate_id):
            job = deps.job_repo.get_by_id(match.job_id)
            if job is None or job.lifecycle_status != JobLifecycleStatus.PUBLISHED:
                continue
            if job.published_at is None or job.published_at < window_start:
                continue
            if deps.agent_decision_repo.exists_for_pair(candidate_id, job.id):
                continue
            pending.append(
                {
                    "job_id": str(job.id),
                    "match_score_id": str(match.id),
                    "overall_score": match.overall_score,
                }
            )
        return {"pending": pending}

    def route_after_pending(state: ApplyAgentState) -> str:
        return "validate_constraints" if state["pending"] else END

    def validate_constraints(state: ApplyAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        config = deps.agent_config_repo.get_by_candidate(candidate_id)
        assert config is not None  # guaranteed by load_config's should_run gate

        results: dict[str, dict[str, object]] = {}
        for pending in state["pending"]:
            job = deps.job_repo.get_by_id(uuid.UUID(pending["job_id"]))
            match = deps.match_score_repo.get_latest_for_pair(
                candidate_id, uuid.UUID(pending["job_id"]), matcher_version=MATCHER_VERSION
            )
            if job is None or match is None:
                results[pending["job_id"]] = {
                    "passed": False,
                    "failures": ["Job no longer available"],
                }
                continue
            results[pending["job_id"]] = evaluate_constraints(config, job, match).as_dict()
        return {"constraint_results": results}

    def decide(state: ApplyAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        applied_today = deps.agent_decision_repo.count_applied_since(candidate_id, today_start)
        cap = state["daily_apply_cap"]

        ordered = sorted(state["pending"], key=lambda p: p["overall_score"], reverse=True)
        plan: list[_Decision] = []
        for pending in ordered:
            result = state["constraint_results"][pending["job_id"]]
            passed = bool(result["passed"])
            failures = list(result["failures"])  # type: ignore[call-overload]
            cap_reached = passed and applied_today >= cap

            if passed and not cap_reached:
                action = "apply"  # intent — `act` attempts it and may downgrade to "skipped"
                applied_today += 1
            else:
                action = AgentDecisionAction.SKIPPED.value

            reason = build_reasoning(
                AgentDecisionAction.APPLIED if action == "apply" else AgentDecisionAction.SKIPPED,
                overall_score=pending["overall_score"],
                constraint_failures=failures,
                cap_reached=cap_reached,
            )

            plan.append(
                {
                    "job_id": pending["job_id"],
                    "match_score_id": pending["match_score_id"],
                    "action": action,
                    "reason": reason,
                    "constraint_results": result,
                }
            )
        return {"plan": plan}

    def act(state: ApplyAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        final: list[_Decision] = []
        for decision in state["plan"]:
            if decision["action"] != "apply":
                final.append(decision)
                continue
            try:
                deps.application_service.apply_to_job(candidate_id, uuid.UUID(decision["job_id"]))
                final.append({**decision, "action": AgentDecisionAction.APPLIED.value})
            except Exception as exc:
                final.append(
                    {
                        **decision,
                        "action": AgentDecisionAction.SKIPPED.value,
                        "reason": f"Skipped — could not apply: {exc}",
                    }
                )
        return {"decisions": final}

    def persist_decisions(state: ApplyAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        now = datetime.now(UTC)
        for decision in state["decisions"]:
            deps.agent_decision_repo.add(
                AgentDecision(
                    id=uuid.uuid4(),
                    candidate_id=candidate_id,
                    job_id=uuid.UUID(decision["job_id"]),
                    match_score_id=uuid.UUID(decision["match_score_id"]),
                    action=AgentDecisionAction(decision["action"]),
                    reason=decision["reason"],
                    constraint_results=decision["constraint_results"],
                    decided_at=now,
                    created_at=now,
                )
            )
        return {}

    graph = StateGraph(ApplyAgentState)
    graph.add_node("load_config", load_config)
    graph.add_node("load_pending_matches", load_pending_matches)
    graph.add_node("validate_constraints", validate_constraints)
    graph.add_node("decide", decide)
    graph.add_node("act", act)
    graph.add_node("persist_decisions", persist_decisions)

    graph.add_edge(START, "load_config")
    graph.add_conditional_edges("load_config", route_after_config, ["load_pending_matches", END])
    graph.add_conditional_edges(
        "load_pending_matches", route_after_pending, ["validate_constraints", END]
    )
    graph.add_edge("validate_constraints", "decide")
    graph.add_edge("decide", "act")
    graph.add_edge("act", "persist_decisions")
    graph.add_edge("persist_decisions", END)

    return graph


def compile_apply_agent_graph(
    deps: ApplyAgentDeps, checkpointer: object
) -> CompiledStateGraph[ApplyAgentState]:
    return build_apply_agent_graph(deps).compile(checkpointer=checkpointer)  # type: ignore[arg-type]
