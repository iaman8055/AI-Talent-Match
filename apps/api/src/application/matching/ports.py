import uuid
from typing import Protocol


class MatchingDispatcher(Protocol):
    """Enqueues async match computation. Triggered whenever a candidate or job finishes
    embedding (see ResumeParsingService.embed_resume / JobParsingService.embed_job) — never
    called from a request-handling code path (CLAUDE.md: never call an LLM/embedding/reranker
    synchronously)."""

    def dispatch_compute_for_candidate(self, candidate_id: uuid.UUID) -> None: ...

    def dispatch_compute_for_job(self, job_id: uuid.UUID) -> None: ...


class RecruiterAgentDispatcher(Protocol):
    """Enqueues the Recruiter Agent (docs/03-ROADMAP.md Phase 7) for a candidate whose matches
    were just recomputed — triggered from MatchingService.compute_matches_for_candidate, never
    from a request-handling code path."""

    def dispatch_for_candidate(self, candidate_id: uuid.UUID) -> None: ...


class ApplyAgentDispatcher(Protocol):
    """Enqueues the Apply Agent (docs/03-ROADMAP.md Phase 6) for a candidate the instant one of
    their match_scores changes — triggered from MatchingService.compute_matches_for_job/
    compute_matches_for_candidate, never from a request-handling code path. This is what makes
    auto-apply feel immediate rather than waiting on the periodic Beat scan
    (run_apply_agent_scan, every 15 min) — that scan still runs as a reconciliation safety net,
    this is the fast path for the common case."""

    def dispatch_for_candidate(self, candidate_id: uuid.UUID) -> None: ...
