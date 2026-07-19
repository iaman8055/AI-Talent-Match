import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class MatchScore:
    id: uuid.UUID
    candidate_id: uuid.UUID
    job_id: uuid.UUID
    overall_score: float
    semantic_score: float
    skill_overlap_score: float
    experience_fit_score: float
    salary_fit_score: float
    location_fit_score: float
    rerank_score: float | None
    matcher_version: str
    candidate_content_hash: str
    job_content_hash: str
    computed_at: datetime
