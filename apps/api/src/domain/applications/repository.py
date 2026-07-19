import uuid
from typing import Protocol

from src.domain.applications.entities import Application


class ApplicationRepository(Protocol):
    def get_by_id(self, application_id: uuid.UUID) -> Application | None: ...

    def get_by_job_and_candidate(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Application | None: ...

    def list_by_job(self, job_id: uuid.UUID) -> list[Application]: ...

    def list_by_candidate(self, candidate_id: uuid.UUID) -> list[Application]: ...

    def add(self, application: Application) -> Application: ...

    def update(self, application: Application) -> Application: ...
