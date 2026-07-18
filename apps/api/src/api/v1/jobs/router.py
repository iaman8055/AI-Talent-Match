import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.deps import (
    get_company_repository,
    get_job_service,
    require_job_membership,
    require_roles,
)
from src.api.v1.jobs.schemas import CreateJobRequest, JobResponse, UpdateJobRequest
from src.application.job.service import JobService
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import Job, Location, WorkMode
from src.domain.user.entities import User, UserRole

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _require_company_member(
    company_id: uuid.UUID, current_user: User, company_repo: CompanyRepository
) -> None:
    if company_repo.get_member(company_id, current_user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this company")


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    body: CreateJobRequest,
    current_user: User = Depends(require_roles(UserRole.RECRUITER)),
    company_repo: CompanyRepository = Depends(get_company_repository),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    _require_company_member(body.company_id, current_user, company_repo)
    job = job_service.create_job(body.company_id, current_user.id, body.title, body.raw_description)
    return JobResponse.from_entity(job)


@router.get("", response_model=list[JobResponse])
def list_jobs(
    company_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.RECRUITER)),
    company_repo: CompanyRepository = Depends(get_company_repository),
    job_service: JobService = Depends(get_job_service),
) -> list[JobResponse]:
    _require_company_member(company_id, current_user, company_repo)
    jobs = job_service.list_jobs(company_id)
    return [JobResponse.from_entity(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job: Job = Depends(require_job_membership()),
) -> JobResponse:
    return JobResponse.from_entity(job)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    body: UpdateJobRequest,
    job: Job = Depends(require_job_membership()),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    updates: dict[str, object] = {}
    for field_name, value in body.model_dump(exclude_unset=True).items():
        if field_name == "location":
            updates["location"] = Location(**value) if value is not None else Location()
        elif field_name == "work_mode":
            updates["work_mode"] = WorkMode(value) if value is not None else None
        else:
            updates[field_name] = value

    job = job_service.update_job(job, updates)
    return JobResponse.from_entity(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job: Job = Depends(require_job_membership()),
    job_service: JobService = Depends(get_job_service),
) -> None:
    job_service.delete_job(job)


@router.post("/{job_id}/publish", response_model=JobResponse)
def publish_job(
    job: Job = Depends(require_job_membership()),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    return JobResponse.from_entity(job_service.publish_job(job))


@router.post("/{job_id}/close", response_model=JobResponse)
def close_job(
    job: Job = Depends(require_job_membership()),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    return JobResponse.from_entity(job_service.close_job(job))


@router.post("/{job_id}/reopen", response_model=JobResponse)
def reopen_job(
    job: Job = Depends(require_job_membership()),
    job_service: JobService = Depends(get_job_service),
) -> JobResponse:
    return JobResponse.from_entity(job_service.reopen_job(job))
