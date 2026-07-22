"""Deterministic decision-reasoning text, composed from structured constraint results and score
data rather than an LLM call. `agent_decisions` is an audit trail for autonomous apply-on-
someone's-behalf actions — it must never fail to write because a model provider is unreachable,
and a templated explanation is more trustworthy here than a possibly-hallucinated one."""

from src.domain.agent.entities import AgentDecisionAction


def build_reasoning(
    action: AgentDecisionAction,
    *,
    overall_score: float,
    constraint_failures: list[str],
    cap_reached: bool = False,
) -> str:
    score = round(overall_score)

    if action == AgentDecisionAction.APPLIED:
        return f"Applied automatically — {score}% match, meets all your configured preferences."

    if cap_reached:
        return "Skipped — your daily auto-apply limit was already reached today."

    if constraint_failures:
        return "Skipped — " + "; ".join(constraint_failures) + "."

    return f"Skipped — {score}% match did not clear your preferences."
