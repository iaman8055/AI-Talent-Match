import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class ResumeStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


@dataclass
class WorkExperience:
    company: str
    title: str
    start_date: date | None
    end_date: date | None
    description: str | None


@dataclass
class Education:
    institution: str
    degree: str | None
    field_of_study: str | None
    start_date: date | None
    end_date: date | None


@dataclass
class Location:
    country: str | None = None
    region: str | None = None
    city: str | None = None


@dataclass
class Candidate:
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    headline: str | None
    summary: str | None
    skills: list[str]
    total_experience_years: float | None
    location: Location
    desired_salary_min: int | None
    desired_salary_max: int | None
    work_mode_preference: WorkMode | None
    work_experience: list[WorkExperience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Resume:
    id: uuid.UUID
    candidate_id: uuid.UUID
    version: int
    s3_key: str
    original_filename: str
    file_type: str  # "pdf" | "docx" — from domain.candidate.file_validation, set once at upload
    content_type: str
    file_size: int
    content_hash: str
    status: ResumeStatus
    parser_version: str
    error_message: str | None
    uploaded_at: datetime
    parsed_at: datetime | None
