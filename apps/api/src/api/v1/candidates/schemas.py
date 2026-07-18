import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from src.domain.candidate.entities import Candidate, Resume, ResumeStatus, WorkMode


class LocationSchema(BaseModel):
    country: str | None = None
    region: str | None = None
    city: str | None = None


class WorkExperienceSchema(BaseModel):
    company: str
    title: str
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None


class EducationSchema(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    start_date: date | None = None
    end_date: date | None = None


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=200)
    headline: str | None = Field(default=None, max_length=300)
    summary: str | None = Field(default=None, max_length=4000)
    skills: list[str] | None = None
    total_experience_years: float | None = Field(default=None, ge=0, le=80)
    location: LocationSchema | None = None
    desired_salary_min: int | None = Field(default=None, ge=0)
    desired_salary_max: int | None = Field(default=None, ge=0)
    work_mode_preference: WorkMode | None = None


class CandidateResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str | None
    headline: str | None
    summary: str | None
    skills: list[str]
    total_experience_years: float | None
    location: LocationSchema
    desired_salary_min: int | None
    desired_salary_max: int | None
    work_mode_preference: WorkMode | None
    work_experience: list[WorkExperienceSchema]
    education: list[EducationSchema]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, candidate: Candidate) -> "CandidateResponse":
        return cls(
            id=candidate.id,
            user_id=candidate.user_id,
            full_name=candidate.full_name,
            headline=candidate.headline,
            summary=candidate.summary,
            skills=candidate.skills,
            total_experience_years=candidate.total_experience_years,
            location=LocationSchema(
                country=candidate.location.country,
                region=candidate.location.region,
                city=candidate.location.city,
            ),
            desired_salary_min=candidate.desired_salary_min,
            desired_salary_max=candidate.desired_salary_max,
            work_mode_preference=candidate.work_mode_preference,
            work_experience=[
                WorkExperienceSchema(
                    company=item.company,
                    title=item.title,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    description=item.description,
                )
                for item in candidate.work_experience
            ],
            education=[
                EducationSchema(
                    institution=item.institution,
                    degree=item.degree,
                    field_of_study=item.field_of_study,
                    start_date=item.start_date,
                    end_date=item.end_date,
                )
                for item in candidate.education
            ],
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )


class ResumeResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    version: int
    original_filename: str
    file_type: str
    content_type: str
    file_size: int
    status: ResumeStatus
    error_message: str | None
    uploaded_at: datetime
    parsed_at: datetime | None

    @classmethod
    def from_entity(cls, resume: Resume) -> "ResumeResponse":
        return cls(
            id=resume.id,
            candidate_id=resume.candidate_id,
            version=resume.version,
            original_filename=resume.original_filename,
            file_type=resume.file_type,
            content_type=resume.content_type,
            file_size=resume.file_size,
            status=resume.status,
            error_message=resume.error_message,
            uploaded_at=resume.uploaded_at,
            parsed_at=resume.parsed_at,
        )


class DownloadUrlResponse(BaseModel):
    url: str
