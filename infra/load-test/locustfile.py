"""Load test for the matching-read pipeline (docs/03-ROADMAP.md Phase 9).

NOT RUN as part of this session, and deliberately so: every simulated candidate here registers
a real account and hits real endpoints, which — against this deployment — means real, metered
calls to NVIDIA's API for embedding (via the async resume-parsing pipeline a real signup would
eventually trigger) and real load on Supabase/Qdrant Cloud's free-tier limits. Actually running
this is a cost/quota decision for whoever operates the target environment, not something to
trigger implicitly.

Usage (once you decide to run it, against an environment you control):
    uv run --project ../../apps/api locust -f locustfile.py --host https://your-api-host

Requires `locust` (not a project dependency — install it in a throwaway venv/container just for
running this, so it never ships as a runtime dependency of the actual application):
    uv run --with locust --project ../../apps/api locust -f locustfile.py --host <url>
"""

import random
import string

from locust import HttpUser, between, task


def _random_email() -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"loadtest-{suffix}@example.com"


class CandidateUser(HttpUser):
    """Simulates the read-heavy candidate loop this app is actually meant to serve well:
    check recommended jobs, check application status. These two endpoints are pure reads
    against already-computed `match_scores` (docs/02-ARCHITECTURE.md §7 — the matching pipeline
    itself is async/Celery, never in the request path), so this is exactly the load profile
    that matters for the "matching pipeline" load target in the roadmap: how the read side
    holds up, not the (already rate-limited, already async) write/compute side."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        email = _random_email()
        password = "LoadTest123!"
        register_response = self.client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "role": "candidate",
                "full_name": "Load Test Candidate",
            },
        )
        if register_response.status_code != 201:
            self.environment.runner.quit()
            return
        self.access_token = register_response.json()["access_token"]

    @property
    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

    @task(3)
    def list_recommended_jobs(self) -> None:
        self.client.get(
            "/candidates/me/recommended-jobs",
            headers=self._auth_headers,
            name="/candidates/me/recommended-jobs",
        )

    @task(2)
    def list_my_applications(self) -> None:
        self.client.get(
            "/applications", headers=self._auth_headers, name="/applications (candidate)"
        )

    @task(1)
    def get_profile(self) -> None:
        self.client.get("/candidates/me", headers=self._auth_headers, name="/candidates/me")


class AuthOnlyUser(HttpUser):
    """Isolates login load specifically, since it's the one endpoint with the tightest rate
    limit (core/rate_limit.py — 5/minute per client IP) — useful for confirming the limit
    actually engages under load rather than only unit-level "does the decorator exist" checks."""

    wait_time = between(1, 2)

    def on_start(self) -> None:
        self.email = _random_email()
        self.password = "LoadTest123!"
        self.client.post(
            "/auth/register",
            json={
                "email": self.email,
                "password": self.password,
                "role": "candidate",
                "full_name": "Load Test Auth",
            },
        )

    @task
    def login(self) -> None:
        self.client.post(
            "/auth/login",
            json={"email": self.email, "password": self.password},
            name="/auth/login",
        )
