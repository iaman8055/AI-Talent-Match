import hashlib
import uuid
from datetime import UTC, datetime

from src.application.candidate.ports import ResumeProcessingDispatcher, StorageClient
from src.application.exceptions import NotFoundError, ValidationError
from src.domain.candidate.entities import Candidate, Location, Resume, ResumeStatus
from src.domain.candidate.file_validation import ALLOWED_RESUME_TYPES, detect_file_signature
from src.domain.candidate.repository import CandidateRepository, ResumeRepository

PARSER_VERSION = "v1"
MAX_RESUME_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
_CONTENT_TYPE_BY_FILE_TYPE = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class CandidateService:
    def __init__(
        self,
        candidate_repo: CandidateRepository,
        resume_repo: ResumeRepository,
        storage: StorageClient,
        dispatcher: ResumeProcessingDispatcher,
    ) -> None:
        self._candidates = candidate_repo
        self._resumes = resume_repo
        self._storage = storage
        self._dispatcher = dispatcher

    def get_or_create_profile(self, user_id: uuid.UUID) -> Candidate:
        candidate = self._candidates.get_by_user_id(user_id)
        if candidate is not None:
            return candidate

        now = datetime.now(UTC)
        candidate = Candidate(
            id=uuid.uuid4(),
            user_id=user_id,
            full_name=None,
            headline=None,
            summary=None,
            skills=[],
            total_experience_years=None,
            location=Location(),
            desired_salary_min=None,
            desired_salary_max=None,
            work_mode_preference=None,
            created_at=now,
            updated_at=now,
        )
        return self._candidates.add(candidate)

    _PROFILE_UPDATE_FIELDS = frozenset(
        {
            "full_name",
            "headline",
            "summary",
            "skills",
            "total_experience_years",
            "location",
            "desired_salary_min",
            "desired_salary_max",
            "work_mode_preference",
        }
    )

    def update_profile(self, user_id: uuid.UUID, updates: dict[str, object]) -> Candidate:
        """`updates` should only contain keys the caller explicitly wants to change (e.g. built
        from a Pydantic request via `model_dump(exclude_unset=True)`), not every profile field."""
        candidate = self.get_or_create_profile(user_id)

        unknown_fields = set(updates) - self._PROFILE_UPDATE_FIELDS
        if unknown_fields:
            raise ValidationError(f"Unknown profile field(s): {', '.join(sorted(unknown_fields))}")

        for field_name, value in updates.items():
            setattr(candidate, field_name, value)

        candidate.updated_at = datetime.now(UTC)
        return self._candidates.update(candidate)

    def upload_resume(
        self,
        user_id: uuid.UUID,
        filename: str,
        file_bytes: bytes,
    ) -> Resume:
        if len(file_bytes) == 0:
            raise ValidationError("Uploaded file is empty")
        if len(file_bytes) > MAX_RESUME_FILE_SIZE_BYTES:
            raise ValidationError("Resume file exceeds the 5MB size limit")

        file_type = detect_file_signature(file_bytes)
        if file_type is None or file_type not in ALLOWED_RESUME_TYPES:
            raise ValidationError("Unsupported file type — only PDF and DOCX resumes are accepted")

        candidate = self.get_or_create_profile(user_id)
        content_hash = hashlib.sha256(file_bytes).hexdigest()

        existing = self._resumes.get_by_content_hash(candidate.id, content_hash)
        if existing is not None:
            return existing

        version = self._resumes.get_latest_version(candidate.id) + 1
        content_type = _CONTENT_TYPE_BY_FILE_TYPE[file_type]
        s3_key = f"resumes/{candidate.id}/{version}-{content_hash[:12]}.{file_type}"

        self._storage.upload(s3_key, file_bytes, content_type)

        now = datetime.now(UTC)
        resume = Resume(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            version=version,
            s3_key=s3_key,
            original_filename=filename,
            file_type=file_type,
            content_type=content_type,
            file_size=len(file_bytes),
            content_hash=content_hash,
            status=ResumeStatus.PENDING,
            parser_version=PARSER_VERSION,
            error_message=None,
            uploaded_at=now,
            parsed_at=None,
        )
        resume = self._resumes.add(resume)
        self._dispatcher.dispatch_parse(resume.id)
        return resume

    def list_resumes(self, user_id: uuid.UUID) -> list[Resume]:
        candidate = self.get_or_create_profile(user_id)
        return self._resumes.list_by_candidate(candidate.id)

    def get_resume(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> Resume:
        candidate = self.get_or_create_profile(user_id)
        resume = self._resumes.get_by_id(resume_id)
        if resume is None or resume.candidate_id != candidate.id:
            raise NotFoundError("Resume not found")
        return resume

    def get_resume_download_url(self, user_id: uuid.UUID, resume_id: uuid.UUID) -> str:
        resume = self.get_resume(user_id, resume_id)
        return self._storage.generate_presigned_url(resume.s3_key, expires_in_seconds=300)
