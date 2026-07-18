import uuid

import pytest
from src.application.exceptions import ConflictError, ValidationError
from src.domain.job.entities import JobLifecycleStatus, JobProcessingStatus, Location, WorkMode

from tests.unit.fakes import build_job_service


class TestCreateAndList:
    def test_create_job_dispatches_parsing(self) -> None:
        harness = build_job_service()
        company_id, user_id = uuid.uuid4(), uuid.uuid4()

        job = harness.service.create_job(company_id, user_id, "Backend Engineer", "We need...")

        assert job.lifecycle_status == JobLifecycleStatus.DRAFT
        assert job.processing_status == JobProcessingStatus.PENDING
        assert job.version == 1
        assert harness.dispatcher.dispatched == [job.id]

    def test_list_jobs_scoped_to_company(self) -> None:
        harness = build_job_service()
        company_a, company_b = uuid.uuid4(), uuid.uuid4()
        user_id = uuid.uuid4()
        harness.service.create_job(company_a, user_id, "Job A", "desc a")
        harness.service.create_job(company_b, user_id, "Job B", "desc b")

        jobs_a = harness.service.list_jobs(company_a)

        assert len(jobs_a) == 1
        assert jobs_a[0].title == "Job A"


class TestUpdateJob:
    def test_update_applies_only_provided_fields(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")

        updated = harness.service.update_job(job, {"summary": "A great role", "salary_min": 100000})

        assert updated.summary == "A great role"
        assert updated.salary_min == 100000
        assert updated.title == "Title"  # untouched

    def test_update_rejects_unknown_field(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")

        with pytest.raises(ValidationError):
            harness.service.update_job(job, {"not_a_real_field": "x"})

    def test_update_can_set_location_and_work_mode(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")

        updated = harness.service.update_job(
            job, {"location": Location(country="US", city="NYC"), "work_mode": WorkMode.REMOTE}
        )

        assert updated.location.city == "NYC"
        assert updated.work_mode == WorkMode.REMOTE

    def test_changing_raw_description_bumps_version_and_redispatches(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "original desc")
        harness.dispatcher.dispatched.clear()

        updated = harness.service.update_job(job, {"raw_description": "a completely new JD"})

        assert updated.version == 2
        assert updated.processing_status == JobProcessingStatus.PENDING
        assert harness.dispatcher.dispatched == [job.id]

    def test_updating_with_identical_description_does_not_redispatch(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "same desc")
        harness.dispatcher.dispatched.clear()

        updated = harness.service.update_job(job, {"raw_description": "same desc"})

        assert updated.version == 1
        assert harness.dispatcher.dispatched == []


class TestLifecycle:
    def _ready_job(self, harness):  # type: ignore[no-untyped-def]
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")
        job.processing_status = JobProcessingStatus.READY
        harness.jobs.update(job)
        return job

    def test_publish_requires_ready_processing_status(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")

        with pytest.raises(ValidationError):
            harness.service.publish_job(job)

    def test_publish_close_reopen_lifecycle(self) -> None:
        harness = build_job_service()
        job = self._ready_job(harness)

        published = harness.service.publish_job(job)
        assert published.lifecycle_status == JobLifecycleStatus.PUBLISHED
        assert published.published_at is not None

        closed = harness.service.close_job(published)
        assert closed.lifecycle_status == JobLifecycleStatus.CLOSED
        assert closed.closed_at is not None

        reopened = harness.service.reopen_job(closed)
        assert reopened.lifecycle_status == JobLifecycleStatus.PUBLISHED
        assert reopened.closed_at is None

    def test_cannot_publish_twice(self) -> None:
        harness = build_job_service()
        job = self._ready_job(harness)
        published = harness.service.publish_job(job)

        with pytest.raises(ConflictError):
            harness.service.publish_job(published)

    def test_cannot_close_a_draft_job(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")

        with pytest.raises(ConflictError):
            harness.service.close_job(job)

    def test_cannot_reopen_a_published_job(self) -> None:
        harness = build_job_service()
        job = self._ready_job(harness)
        published = harness.service.publish_job(job)

        with pytest.raises(ConflictError):
            harness.service.reopen_job(published)


class TestDelete:
    def test_delete_draft_job(self) -> None:
        harness = build_job_service()
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")

        harness.service.delete_job(job)

        assert harness.jobs.get_by_id(job.id) is None

    def test_cannot_delete_published_job(self) -> None:
        harness = build_job_service()
        job = self._published_job(harness)

        with pytest.raises(ConflictError):
            harness.service.delete_job(job)

    def _published_job(self, harness):  # type: ignore[no-untyped-def]
        job = harness.service.create_job(uuid.uuid4(), uuid.uuid4(), "Title", "desc")
        job.processing_status = JobProcessingStatus.READY
        harness.jobs.update(job)
        return harness.service.publish_job(job)
