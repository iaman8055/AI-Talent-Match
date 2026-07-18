import uuid

import pytest
from src.application.exceptions import NotFoundError, ValidationError
from src.domain.candidate.entities import Location, WorkMode

from tests.unit.fakes import build_candidate_service

_VALID_PDF_BYTES = b"%PDF-1.4\n%fake pdf content for tests\n"
_VALID_DOCX_BYTES = b"PK\x03\x04fake docx bytes for tests"


class TestProfile:
    def test_get_or_create_profile_is_idempotent(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        first = harness.service.get_or_create_profile(user_id)
        second = harness.service.get_or_create_profile(user_id)

        assert first.id == second.id

    def test_update_profile_applies_only_provided_fields(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()
        harness.service.get_or_create_profile(user_id)

        updated = harness.service.update_profile(user_id, {"full_name": "Jane Doe"})
        assert updated.full_name == "Jane Doe"
        assert updated.headline is None

        updated_again = harness.service.update_profile(
            user_id, {"headline": "Senior Engineer", "work_mode_preference": WorkMode.REMOTE}
        )
        assert updated_again.full_name == "Jane Doe"  # untouched by the second call
        assert updated_again.headline == "Senior Engineer"
        assert updated_again.work_mode_preference == WorkMode.REMOTE

    def test_update_profile_rejects_unknown_field(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        with pytest.raises(ValidationError):
            harness.service.update_profile(user_id, {"not_a_real_field": "x"})

    def test_update_profile_can_set_location(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        updated = harness.service.update_profile(
            user_id, {"location": Location(country="US", region="CA", city="SF")}
        )

        assert updated.location.city == "SF"


class TestResumeUpload:
    def test_upload_valid_pdf_creates_resume_and_dispatches_parsing(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        resume = harness.service.upload_resume(user_id, "resume.pdf", _VALID_PDF_BYTES)

        assert resume.file_type == "pdf"
        assert resume.version == 1
        assert harness.dispatcher.dispatched == [resume.id]
        assert harness.storage.files[resume.s3_key] == _VALID_PDF_BYTES

    def test_upload_valid_docx_is_accepted(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        resume = harness.service.upload_resume(user_id, "resume.docx", _VALID_DOCX_BYTES)

        assert resume.file_type == "docx"

    def test_upload_rejects_unsupported_file_type(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        with pytest.raises(ValidationError):
            harness.service.upload_resume(user_id, "resume.txt", b"just plain text, not a resume")

    def test_upload_rejects_empty_file(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        with pytest.raises(ValidationError):
            harness.service.upload_resume(user_id, "resume.pdf", b"")

    def test_upload_rejects_oversized_file(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()
        oversized = _VALID_PDF_BYTES + b"0" * (5 * 1024 * 1024)

        with pytest.raises(ValidationError):
            harness.service.upload_resume(user_id, "resume.pdf", oversized)

    def test_reuploading_identical_bytes_dedupes_instead_of_creating_a_new_version(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()

        first = harness.service.upload_resume(user_id, "resume.pdf", _VALID_PDF_BYTES)
        second = harness.service.upload_resume(user_id, "resume.pdf", _VALID_PDF_BYTES)

        assert first.id == second.id
        assert harness.dispatcher.dispatched == [first.id]  # only dispatched once

    def test_second_distinct_upload_gets_version_two(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()
        harness.service.upload_resume(user_id, "resume.pdf", _VALID_PDF_BYTES)

        second = harness.service.upload_resume(user_id, "resume-v2.pdf", _VALID_PDF_BYTES + b"more")

        assert second.version == 2


class TestResumeAccess:
    def test_list_resumes_returns_only_this_users_resumes(self) -> None:
        harness = build_candidate_service()
        user_a, user_b = uuid.uuid4(), uuid.uuid4()
        harness.service.upload_resume(user_a, "a.pdf", _VALID_PDF_BYTES)
        harness.service.upload_resume(user_b, "b.pdf", _VALID_PDF_BYTES + b"different")

        resumes_a = harness.service.list_resumes(user_a)

        assert len(resumes_a) == 1
        assert resumes_a[0].original_filename == "a.pdf"

    def test_get_resume_from_another_user_raises_not_found(self) -> None:
        harness = build_candidate_service()
        owner, other = uuid.uuid4(), uuid.uuid4()
        resume = harness.service.upload_resume(owner, "a.pdf", _VALID_PDF_BYTES)

        with pytest.raises(NotFoundError):
            harness.service.get_resume(other, resume.id)

    def test_get_resume_download_url(self) -> None:
        harness = build_candidate_service()
        user_id = uuid.uuid4()
        resume = harness.service.upload_resume(user_id, "a.pdf", _VALID_PDF_BYTES)

        url = harness.service.get_resume_download_url(user_id, resume.id)

        assert resume.s3_key in url
