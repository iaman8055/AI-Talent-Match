import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.job.entities import Job, JobLifecycleStatus, JobProcessingStatus, WorkMode


class LocationSchema(BaseModel):
    country: str | None = None
    region: str | None = None
    city: str | None = None


class CreateJobRequest(BaseModel):
    company_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    raw_description: str = Field(min_length=1, max_length=20000)


class UpdateJobRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    raw_description: str | None = Field(default=None, min_length=1, max_length=20000)
    summary: str | None = Field(default=None, max_length=4000)
    required_skills: list[str] | None = None
    nice_to_have_skills: list[str] | None = None
    responsibilities: list[str] | None = None
    qualifications: list[str] | None = None
    min_experience_years: float | None = Field(default=None, ge=0, le=80)
    employment_type: str | None = Field(default=None, max_length=50)
    work_mode: WorkMode | None = None
    location: LocationSchema | None = None
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)


class JobResponse(BaseModel):
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
    location: LocationSchema
    salary_min: int | None
    salary_max: int | None
    lifecycle_status: JobLifecycleStatus
    processing_status: JobProcessingStatus
    error_message: str | None
    version: int
    published_at: datetime | None
    closed_at: datetime | None
    parsed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, job: Job) -> "JobResponse":
        return cls(
            id=job.id,
            company_id=job.company_id,
            created_by_user_id=job.created_by_user_id,
            title=job.title,
            raw_description=job.raw_description,
            summary=job.summary,
            required_skills=job.required_skills,
            nice_to_have_skills=job.nice_to_have_skills,
            responsibilities=job.responsibilities,
            qualifications=job.qualifications,
            min_experience_years=job.min_experience_years,
            employment_type=job.employment_type,
            work_mode=job.work_mode,
            location=LocationSchema(
                country=job.location.country,
                region=job.location.region,
                city=job.location.city,
            ),
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            lifecycle_status=job.lifecycle_status,
            processing_status=job.processing_status,
            error_message=job.error_message,
            version=job.version,
            published_at=job.published_at,
            closed_at=job.closed_at,
            parsed_at=job.parsed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
