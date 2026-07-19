import uuid
from datetime import UTC, datetime

import pytest
from src.application.exceptions import ConflictError, NotFoundError
from src.domain.applications.entities import Application, ApplicationStatus
from src.domain.job.entities import JobLifecycleStatus
from src.domain.user.entities import User, UserRole

from tests.unit.application.test_matching_service import _make_candidate, _make_company, _make_job
from tests.unit.fakes import ApplicationServiceHarness, build_application_service


def _make_user(role: UserRole = UserRole.CANDIDATE, **overrides: object) -> User:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        email="candidate@example.com",
        role=role,
        full_name="Jane Doe",
        password_hash="irrelevant",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]


class TestInviteCandidate:
    def test_creates_application_and_sends_email(self) -> None:
        harness = build_application_service()
        company = harness.companies.add(_make_company())
        job = harness.jobs.add(_make_job(company_id=company.id))
        candidate_user = harness.users.add(_make_user())
        candidate = harness.candidates.add(_make_candidate(user_id=candidate_user.id))
        recruiter_id = uuid.uuid4()

        application = harness.service.invite_candidate(job, candidate.id, recruiter_id)

        assert application.status == ApplicationStatus.INVITED
        assert application.invited_by_user_id == recruiter_id
        assert application.job_id == job.id
        assert application.candidate_id == candidate.id
        assert len(harness.email_sender.sent) == 1
        assert harness.email_sender.sent[0][1] == candidate_user.email

    def test_raises_if_candidate_missing(self) -> None:
        harness = build_application_service()
        company = harness.companies.add(_make_company())
        job = harness.jobs.add(_make_job(company_id=company.id))

        with pytest.raises(NotFoundError):
            harness.service.invite_candidate(job, uuid.uuid4(), uuid.uuid4())

    def test_reinviting_already_invited_candidate_is_idempotent(self) -> None:
        harness = build_application_service()
        company = harness.companies.add(_make_company())
        job = harness.jobs.add(_make_job(company_id=company.id))
        candidate_user = harness.users.add(_make_user())
        candidate = harness.candidates.add(_make_candidate(user_id=candidate_user.id))

        first = harness.service.invite_candidate(job, candidate.id, uuid.uuid4())
        second = harness.service.invite_candidate(job, candidate.id, uuid.uuid4())

        assert first.id == second.id
        assert len(harness.email_sender.sent) == 2  # resent, but no duplicate row

    def test_inviting_already_applied_candidate_raises_conflict(self) -> None:
        harness = build_application_service()
        company = harness.companies.add(_make_company())
        job = harness.jobs.add(_make_job(company_id=company.id))
        candidate_user = harness.users.add(_make_user())
        candidate = harness.candidates.add(_make_candidate(user_id=candidate_user.id))
        harness.service.apply_to_job(candidate.id, job.id)

        with pytest.raises(ConflictError):
            harness.service.invite_candidate(job, candidate.id, uuid.uuid4())


class TestApplyToJob:
    def test_creates_application_directly_when_not_previously_invited(self) -> None:
        harness = build_application_service()
        job = harness.jobs.add(_make_job())
        candidate = harness.candidates.add(_make_candidate())

        application = harness.service.apply_to_job(candidate.id, job.id)

        assert application.status == ApplicationStatus.APPLIED
        assert application.applied_at is not None

    def test_advances_invited_application_to_applied(self) -> None:
        harness = build_application_service()
        job = harness.jobs.add(_make_job())
        candidate_user = harness.users.add(_make_user())
        candidate = harness.candidates.add(_make_candidate(user_id=candidate_user.id))
        invited = harness.service.invite_candidate(job, candidate.id, uuid.uuid4())

        applied = harness.service.apply_to_job(candidate.id, job.id)

        assert applied.id == invited.id
        assert applied.status == ApplicationStatus.APPLIED

    def test_raises_if_job_not_published(self) -> None:
        harness = build_application_service()
        job = harness.jobs.add(_make_job(lifecycle_status=JobLifecycleStatus.DRAFT))
        candidate = harness.candidates.add(_make_candidate())

        with pytest.raises(ConflictError):
            harness.service.apply_to_job(candidate.id, job.id)

    def test_raises_if_already_applied(self) -> None:
        harness = build_application_service()
        job = harness.jobs.add(_make_job())
        candidate = harness.candidates.add(_make_candidate())
        harness.service.apply_to_job(candidate.id, job.id)

        with pytest.raises(ConflictError):
            harness.service.apply_to_job(candidate.id, job.id)

    def test_raises_if_job_missing(self) -> None:
        harness = build_application_service()
        candidate = harness.candidates.add(_make_candidate())

        with pytest.raises(NotFoundError):
            harness.service.apply_to_job(candidate.id, uuid.uuid4())


class TestPipelineTransitions:
    def _applied_application(self, harness: ApplicationServiceHarness) -> Application:
        job = harness.jobs.add(_make_job())
        candidate = harness.candidates.add(_make_candidate())
        return harness.service.apply_to_job(candidate.id, job.id)

    def test_full_happy_path(self) -> None:
        harness = build_application_service()
        application = self._applied_application(harness)

        screening = harness.service.screen_application(application)
        assert screening.status == ApplicationStatus.SCREENING

        interview = harness.service.interview_application(screening)
        assert interview.status == ApplicationStatus.INTERVIEW

        offer = harness.service.offer_application(interview)
        assert offer.status == ApplicationStatus.OFFER

    def test_reject_from_any_non_rejected_stage(self) -> None:
        harness = build_application_service()
        application = self._applied_application(harness)

        rejected = harness.service.reject_application(application)
        assert rejected.status == ApplicationStatus.REJECTED

    def test_rejecting_already_rejected_raises_conflict(self) -> None:
        harness = build_application_service()
        application = self._applied_application(harness)
        rejected = harness.service.reject_application(application)

        with pytest.raises(ConflictError):
            harness.service.reject_application(rejected)

    def test_screen_requires_applied_status(self) -> None:
        harness = build_application_service()
        job = harness.jobs.add(_make_job())
        candidate_user = harness.users.add(_make_user())
        candidate = harness.candidates.add(_make_candidate(user_id=candidate_user.id))
        invited = harness.service.invite_candidate(job, candidate.id, uuid.uuid4())

        with pytest.raises(ConflictError):
            harness.service.screen_application(invited)

    def test_interview_requires_screening_status(self) -> None:
        harness = build_application_service()
        application = self._applied_application(harness)

        with pytest.raises(ConflictError):
            harness.service.interview_application(application)

    def test_offer_requires_interview_status(self) -> None:
        harness = build_application_service()
        application = self._applied_application(harness)
        screening = harness.service.screen_application(application)

        with pytest.raises(ConflictError):
            harness.service.offer_application(screening)
