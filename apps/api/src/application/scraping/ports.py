from typing import Protocol, TypedDict


class ScrapedJobPosting(TypedDict):
    external_id: str
    title: str
    company_name: str
    location_text: str | None
    raw_description: str
    url: str


class JobScraperClient(Protocol):
    """Fetches raw postings from an external job source — no filtering/relevance logic belongs
    here, that happens via the ingestion service's query targeting and the LLM extraction
    pipeline downstream, same as a recruiter-posted job."""

    def search_job_ids(self, query: str, max_results: int) -> list[str]: ...

    def fetch_job_detail(self, job_id: str) -> ScrapedJobPosting | None: ...
