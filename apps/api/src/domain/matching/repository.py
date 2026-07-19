import uuid
from typing import Protocol

from src.domain.matching.entities import MatchScore


class MatchScoreRepository(Protocol):
    def add(self, match_score: MatchScore) -> MatchScore: ...

    def get_latest_for_pair(
        self, candidate_id: uuid.UUID, job_id: uuid.UUID, matcher_version: str
    ) -> MatchScore | None:
        """Most recent row for this (candidate, job, matcher_version) triple, if any — used to
        decide whether a recompute can be skipped (see MatchingService's content-hash check)."""
        ...

    def list_latest_for_job(self, job_id: uuid.UUID) -> list[MatchScore]:
        """One row per candidate — the latest score for each candidate ever matched against this
        job, unfiltered by threshold (callers apply the threshold at read time)."""
        ...

    def list_latest_for_candidate(self, candidate_id: uuid.UUID) -> list[MatchScore]:
        """One row per job — the latest score for each job ever matched against this candidate."""
        ...
