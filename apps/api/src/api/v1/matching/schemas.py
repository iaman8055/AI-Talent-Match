from datetime import datetime

from pydantic import BaseModel

from src.api.v1.candidates.schemas import CandidateResponse
from src.api.v1.jobs.schemas import JobResponse
from src.domain.matching.entities import MatchScore


class MatchScoreDetail(BaseModel):
    overall_score: float
    semantic_score: float
    skill_overlap_score: float
    experience_fit_score: float
    salary_fit_score: float
    location_fit_score: float
    rerank_score: float | None
    matcher_version: str
    computed_at: datetime

    @classmethod
    def from_entity(cls, score: MatchScore) -> "MatchScoreDetail":
        return cls(
            overall_score=score.overall_score,
            semantic_score=score.semantic_score,
            skill_overlap_score=score.skill_overlap_score,
            experience_fit_score=score.experience_fit_score,
            salary_fit_score=score.salary_fit_score,
            location_fit_score=score.location_fit_score,
            rerank_score=score.rerank_score,
            matcher_version=score.matcher_version,
            computed_at=score.computed_at,
        )


class JobCandidateMatchResponse(BaseModel):
    candidate: CandidateResponse
    match: MatchScoreDetail
    has_pending_outreach_draft: bool


class RecommendedJobResponse(BaseModel):
    job: JobResponse
    match: MatchScoreDetail
