import uuid
from datetime import UTC, datetime

from src.application.auth.ports import EmailSender
from src.application.exceptions import ConflictError, NotFoundError
from src.domain.applications.entities import Application, ApplicationStatus
from src.domain.applications.repository import ApplicationRepository
from src.domain.candidate.repository import CandidateRepository
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import Job, JobLifecycleStatus
from src.domain.job.repository import JobRepository
from src.domain.user.repository import UserRepository


class ApplicationService:
    def __init__(
        self,
        application_repo: ApplicationRepository,
        job_repo: JobRepository,
        candidate_repo: CandidateRepository,
        user_repo: UserRepository,
        company_repo: CompanyRepository,
        email_sender: EmailSender,
    ) -> None:
        self._applications = application_repo
        self._jobs = job_repo
        self._candidates = candidate_repo
        self._users = user_repo
        self._companies = company_repo
        self._email_sender = email_sender

    def invite_candidate(
        self, job: Job, candidate_id: uuid.UUID, invited_by_user_id: uuid.UUID
    ) -> Application:
        candidate = self._candidates.get_by_id(candidate_id)
        if candidate is None:
            raise NotFoundError("Candidate not found")

        existing = self._applications.get_by_job_and_candidate(job.id, candidate.id)
        now = datetime.now(UTC)
        if existing is None:
            application = Application(
                id=uuid.uuid4(),
                job_id=job.id,
                candidate_id=candidate.id,
                status=ApplicationStatus.INVITED,
                invited_by_user_id=invited_by_user_id,
                applied_at=None,
                status_updated_at=now,
                created_at=now,
                updated_at=now,
            )
            application = self._applications.add(application)
        elif existing.status == ApplicationStatus.INVITED:
            application = existing  # idempotent re-invite — just resend the email below
        else:
            raise ConflictError(
                f"Candidate already has an application in status '{existing.status}'"
            )

        candidate_user = self._users.get_by_id(candidate.user_id)
        company = self._companies.get_by_id(job.company_id)
        if candidate_user is not None and company is not None:
            self._email_sender.send_candidate_invite_email(
                candidate_user, job.id, job.title, company.name
            )
        return application

    def apply_to_job(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> Application:
        job = self._jobs.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Job not found")
        if job.lifecycle_status != JobLifecycleStatus.PUBLISHED:
            raise ConflictError("Can only apply to published jobs")

        existing = self._applications.get_by_job_and_candidate(job_id, candidate_id)
        now = datetime.now(UTC)
        if existing is None:
            application = Application(
                id=uuid.uuid4(),
                job_id=job_id,
                candidate_id=candidate_id,
                status=ApplicationStatus.APPLIED,
                invited_by_user_id=None,
                applied_at=now,
                status_updated_at=now,
                created_at=now,
                updated_at=now,
            )
            return self._applications.add(application)

        if existing.status == ApplicationStatus.INVITED:
            existing.status = ApplicationStatus.APPLIED
            existing.applied_at = now
            existing.status_updated_at = now
            existing.updated_at = now
            return self._applications.update(existing)

        raise ConflictError(f"Application already exists with status '{existing.status}'")

    def screen_application(self, application: Application) -> Application:
        if application.status != ApplicationStatus.APPLIED:
            raise ConflictError("Only applied candidates can move to screening")
        return self._transition(application, ApplicationStatus.SCREENING)

    def interview_application(self, application: Application) -> Application:
        if application.status != ApplicationStatus.SCREENING:
            raise ConflictError("Only screening candidates can move to interview")
        return self._transition(application, ApplicationStatus.INTERVIEW)

    def offer_application(self, application: Application) -> Application:
        if application.status != ApplicationStatus.INTERVIEW:
            raise ConflictError("Only interviewing candidates can be offered")
        return self._transition(application, ApplicationStatus.OFFER)

    def reject_application(self, application: Application) -> Application:
        if application.status == ApplicationStatus.REJECTED:
            raise ConflictError("Application is already rejected")
        return self._transition(application, ApplicationStatus.REJECTED)

    def _transition(self, application: Application, new_status: ApplicationStatus) -> Application:
        now = datetime.now(UTC)
        application.status = new_status
        application.status_updated_at = now
        application.updated_at = now
        return self._applications.update(application)
