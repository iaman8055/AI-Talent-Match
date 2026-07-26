from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from src.application.scraping.ports import ScrapedJobPosting

_SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
_DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
_PAGE_SIZE = 25
_MAX_DESCRIPTION_CHARS = 8000

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


class LinkedInGuestClient:
    """Fetches raw job postings from LinkedIn's public, unauthenticated "jobs-guest" endpoints —
    the same ones used interactively when browsing linkedin.com/jobs without being signed in.
    Deliberately does no relevance/quality filtering (that's the deleted TITLE_BLOCKLIST/
    AI_STRONG/AI_WEAK gate from the original script) — every posting found is returned as-is and
    filtering happens downstream via query targeting + the LLM extraction pipeline, same as a
    recruiter-posted job. Scraping this endpoint is against LinkedIn's Terms of Service; this is
    a product-risk decision made by the caller, not something this client can mitigate."""

    def __init__(self, location: str = "India", timeout: float = 10.0) -> None:
        self._location = location
        self._timeout = timeout

    def search_job_ids(self, query: str, max_results: int) -> list[str]:
        ids: list[str] = []
        with httpx.Client(headers=_HEADERS, timeout=self._timeout) as client:
            start = 0
            while len(ids) < max_results:
                url = (
                    f"{_SEARCH_URL}?keywords={quote(query)}&location={quote(self._location)}"
                    f"&start={start}"
                )
                response = client.get(url)
                if response.status_code != 200:
                    break
                soup = BeautifulSoup(response.text, "html.parser")
                cards = soup.find_all("div", {"class": "base-card"})
                if not cards:
                    break
                for card in cards:
                    urn = str(card.get("data-entity-urn", ""))
                    job_id = urn.split(":")[-1]
                    if job_id and job_id not in ids:
                        ids.append(job_id)
                start += _PAGE_SIZE
        return ids[:max_results]

    def fetch_job_detail(self, job_id: str) -> ScrapedJobPosting | None:
        with httpx.Client(headers=_HEADERS, timeout=self._timeout) as client:
            response = client.get(_DETAIL_URL.format(job_id=job_id))
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        def text(selector: str) -> str:
            el = soup.select_one(selector)
            return el.get_text(strip=True) if el else ""

        title = text("h2.top-card-layout__title")
        company = text("a.topcard__org-name-link") or text("span.topcard__flavor")
        location_text = text("span.topcard__flavor--bullet") or None
        description_el = soup.select_one("div.description__text")
        description = (
            description_el.get_text(separator=" ", strip=True)[:_MAX_DESCRIPTION_CHARS]
            if description_el
            else ""
        )

        if not title or not description:
            return None

        return {
            "external_id": job_id,
            "title": title,
            "company_name": company or "Unknown",
            "location_text": location_text,
            "raw_description": description,
            "url": f"https://www.linkedin.com/jobs/view/{job_id}",
        }
