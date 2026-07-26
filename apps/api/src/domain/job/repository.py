import uuid
from typing import Protocol

from src.domain.job.entities import Job, JobSource, JobVersion


class JobRepository(Protocol):
    def get_by_id(self, job_id: uuid.UUID) -> Job | None: ...

    def list_by_company(self, company_id: uuid.UUID) -> list[Job]: ...

    def get_by_source_and_external_id(self, source: JobSource, external_id: str) -> Job | None: ...

    def search_published(self, query: str | None, location: str | None) -> list[Job]:
        """Published jobs (any source) matching an optional title keyword and/or location
        substring — a plain keyword search, not semantic matching (that's the vector-search path
        in MatchingService). Case-insensitive; blank/None filters are ignored."""
        ...

    def add(self, job: Job) -> Job: ...

    def update(self, job: Job) -> Job: ...

    def delete(self, job_id: uuid.UUID) -> None: ...


class JobVersionRepository(Protocol):
    def add(self, version: JobVersion) -> JobVersion: ...

    def list_by_job(self, job_id: uuid.UUID) -> list[JobVersion]: ...
