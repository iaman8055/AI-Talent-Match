import uuid
from typing import Protocol


class MatchingDispatcher(Protocol):
    """Enqueues async match computation. Triggered whenever a candidate or job finishes
    embedding (see ResumeParsingService.embed_resume / JobParsingService.embed_job) — never
    called from a request-handling code path (CLAUDE.md: never call an LLM/embedding/reranker
    synchronously)."""

    def dispatch_compute_for_candidate(self, candidate_id: uuid.UUID) -> None: ...

    def dispatch_compute_for_job(self, job_id: uuid.UUID) -> None: ...
