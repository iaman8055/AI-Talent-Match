import uuid
from typing import Protocol


class JobProcessingDispatcher(Protocol):
    """Enqueues async processing for a newly created/edited job. Implemented via Celery's
    `.delay()` in infrastructure/tasks — kept behind a port so the application layer never
    imports Celery directly."""

    def dispatch_parse(self, job_id: uuid.UUID) -> None: ...
