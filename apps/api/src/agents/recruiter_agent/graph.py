"""The Recruiter Agent graph (docs/02-ARCHITECTURE.md §5): triggered right after
`MatchingService.compute_matches_for_candidate` persists fresh `match_scores` for a candidate
(see application/matching/service.py). Finds this candidate's newly-high-match published jobs —
"newly" meaning no `OutreachDraft` has ever been generated for that (candidate, job) pair — and
generates a recruiter-facing summary + draft outreach message for each, for a human recruiter to
review, edit, send, or discard. Nothing here is ever auto-sent (docs/01-ANALYSIS.md row 12).

Unlike the Apply Agent (agents/apply_agent/graph.py), this graph has no Postgres checkpointer:
it runs once, synchronously, per real event, inside one Celery task with the app's standard
retry/backoff, and the `exists_for_pair` dedup makes a retried run idempotent — there's no
scheduled batch scan here whose lost progress would need resuming.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src.application.ai.ports import LLMClient
from src.application.company.service import DEFAULT_MATCH_THRESHOLD
from src.application.matching.scoring import MATCHER_VERSION
from src.application.notifications.service import NotificationService
from src.application.outreach.generation_schema import (
    OUTREACH_DRAFT_INSTRUCTIONS,
    OutreachDraftGenerationResult,
)
from src.domain.candidate.entities import Candidate
from src.domain.candidate.repository import CandidateRepository
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import Job, JobLifecycleStatus
from src.domain.job.repository import JobRepository
from src.domain.matching.repository import MatchScoreRepository
from src.domain.notifications.entities import NotificationType
from src.domain.outreach.entities import OutreachDraft, OutreachDraftStatus
from src.domain.outreach.repository import OutreachDraftRepository


class _PendingMatch(TypedDict):
    job_id: str
    match_score_id: str
    overall_score: float


class _GeneratedDraft(TypedDict):
    job_id: str
    match_score_id: str
    candidate_summary: str
    subject: str
    body: str


class RecruiterAgentState(TypedDict):
    candidate_id: str
    should_run: bool
    pending: list[_PendingMatch]
    generated: list[_GeneratedDraft]


@dataclass
class RecruiterAgentDeps:
    """Built fresh per Celery task invocation — same one-session-per-task discipline as every
    other Celery task in this app (see infrastructure/tasks/matching_tasks.py)."""

    candidate_repo: CandidateRepository
    job_repo: JobRepository
    company_repo: CompanyRepository
    match_score_repo: MatchScoreRepository
    outreach_draft_repo: OutreachDraftRepository
    notification_service: NotificationService
    llm_client: LLMClient


def _candidate_facts(candidate: Candidate) -> dict[str, object]:
    return {
        "headline": candidate.headline,
        "summary": candidate.summary,
        "skills": candidate.skills,
        "total_experience_years": candidate.total_experience_years,
    }


def _job_facts(job: Job) -> dict[str, object]:
    return {
        "title": job.title,
        "summary": job.summary,
        "required_skills": job.required_skills,
        "responsibilities": job.responsibilities,
    }


def build_recruiter_agent_graph(deps: RecruiterAgentDeps) -> StateGraph[RecruiterAgentState]:
    def load_candidate(state: RecruiterAgentState) -> dict[str, object]:
        candidate = deps.candidate_repo.get_by_id(uuid.UUID(state["candidate_id"]))
        return {"should_run": candidate is not None}

    def route_after_load(state: RecruiterAgentState) -> str:
        return "find_new_high_matches" if state["should_run"] else END

    def find_new_high_matches(state: RecruiterAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        pending: list[_PendingMatch] = []
        for match in deps.match_score_repo.list_latest_for_candidate(candidate_id):
            if match.matcher_version != MATCHER_VERSION:
                continue
            job = deps.job_repo.get_by_id(match.job_id)
            if job is None or job.lifecycle_status != JobLifecycleStatus.PUBLISHED:
                continue
            company = deps.company_repo.get_by_id(job.company_id)
            threshold = company.match_threshold if company is not None else DEFAULT_MATCH_THRESHOLD
            if match.overall_score < threshold:
                continue
            if deps.outreach_draft_repo.exists_for_pair(candidate_id, job.id):
                continue
            pending.append(
                {
                    "job_id": str(job.id),
                    "match_score_id": str(match.id),
                    "overall_score": match.overall_score,
                }
            )
        return {"pending": pending}

    def route_after_pending(state: RecruiterAgentState) -> str:
        return "generate_drafts" if state["pending"] else END

    def generate_drafts(state: RecruiterAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        candidate = deps.candidate_repo.get_by_id(candidate_id)
        if candidate is None:
            return {"generated": []}

        candidate_data = _candidate_facts(candidate)
        generated: list[_GeneratedDraft] = []
        for pending in state["pending"]:
            job = deps.job_repo.get_by_id(uuid.UUID(pending["job_id"]))
            if job is None:
                continue
            data = json.dumps({"candidate": candidate_data, "job": _job_facts(job)})
            try:
                result = deps.llm_client.extract_structured(
                    OUTREACH_DRAFT_INSTRUCTIONS, data, OutreachDraftGenerationResult
                )
            except Exception:  # one bad generation shouldn't drop the whole batch
                continue
            generated.append(
                {
                    "job_id": pending["job_id"],
                    "match_score_id": pending["match_score_id"],
                    "candidate_summary": result.candidate_summary,
                    "subject": result.subject,
                    "body": result.body,
                }
            )
        return {"generated": generated}

    def persist_drafts(state: RecruiterAgentState) -> dict[str, object]:
        candidate_id = uuid.UUID(state["candidate_id"])
        candidate = deps.candidate_repo.get_by_id(candidate_id)
        now = datetime.now(UTC)
        for draft in state["generated"]:
            job_id = uuid.UUID(draft["job_id"])
            deps.outreach_draft_repo.add(
                OutreachDraft(
                    id=uuid.uuid4(),
                    candidate_id=candidate_id,
                    job_id=job_id,
                    match_score_id=uuid.UUID(draft["match_score_id"]),
                    candidate_summary=draft["candidate_summary"],
                    subject=draft["subject"],
                    body=draft["body"],
                    status=OutreachDraftStatus.DRAFT,
                    sent_by_user_id=None,
                    sent_at=None,
                    created_at=now,
                    updated_at=now,
                )
            )

            job = deps.job_repo.get_by_id(job_id)
            if job is None:
                continue
            candidate_name = (candidate.full_name if candidate else None) or "A candidate"
            for member in deps.company_repo.list_members(job.company_id):
                deps.notification_service.notify(
                    member.user_id,
                    NotificationType.NEW_OUTREACH_DRAFT,
                    f"New high match for {job.title}",
                    f"{candidate_name} newly cleared your match threshold — a draft outreach "
                    "message is ready to review.",
                    link="/recruiter/outreach",
                )
        return {}

    graph = StateGraph(RecruiterAgentState)
    graph.add_node("load_candidate", load_candidate)
    graph.add_node("find_new_high_matches", find_new_high_matches)
    graph.add_node("generate_drafts", generate_drafts)
    graph.add_node("persist_drafts", persist_drafts)

    graph.add_edge(START, "load_candidate")
    graph.add_conditional_edges("load_candidate", route_after_load, ["find_new_high_matches", END])
    graph.add_conditional_edges(
        "find_new_high_matches", route_after_pending, ["generate_drafts", END]
    )
    graph.add_edge("generate_drafts", "persist_drafts")
    graph.add_edge("persist_drafts", END)

    return graph
