import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class JobLifecycleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class JobProcessingStatus(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    PARSED = "parsed"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"


class WorkMode(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


@dataclass
class Location:
    country: str | None = None
    region: str | None = None
    city: str | None = None


@dataclass
class Job:
    id: uuid.UUID
    company_id: uuid.UUID
    created_by_user_id: uuid.UUID
    title: str
    raw_description: str
    summary: str | None
    required_skills: list[str]
    nice_to_have_skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]
    min_experience_years: float | None
    employment_type: str | None
    work_mode: WorkMode | None
    location: Location
    salary_min: int | None
    salary_max: int | None
    lifecycle_status: JobLifecycleStatus
    processing_status: JobProcessingStatus
    parser_version: str | None
    content_hash: str
    error_message: str | None
    version: int
    published_at: datetime | None
    closed_at: datetime | None
    parsed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass
class JobVersion:
    id: uuid.UUID
    job_id: uuid.UUID
    version: int
    raw_description: str
    content_hash: str
    parser_version: str
    extracted_snapshot: dict[str, object]
    created_at: datetime
