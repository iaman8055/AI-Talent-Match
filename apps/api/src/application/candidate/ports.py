import uuid
from typing import Protocol


class StorageClient(Protocol):
    def ensure_bucket(self) -> None: ...

    def upload(self, key: str, data: bytes, content_type: str) -> None: ...

    def download(self, key: str) -> bytes: ...

    def generate_presigned_url(self, key: str, expires_in_seconds: int) -> str: ...


class TextExtractor(Protocol):
    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        """`file_type` is one of domain.candidate.file_validation.ALLOWED_RESUME_TYPES."""
        ...


class ResumeProcessingDispatcher(Protocol):
    """Enqueues async processing for a newly uploaded resume. Implemented via Celery's
    `.delay()` in infrastructure/tasks — kept behind a port so the application layer never
    imports Celery directly."""

    def dispatch_parse(self, resume_id: uuid.UUID) -> None: ...
