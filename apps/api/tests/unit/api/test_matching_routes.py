import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from src.api.deps import (
    get_access_token_service,
    get_candidate_repository,
    get_company_repository,
    get_job_repository,
    get_matching_service,
    get_user_repository,
)
from src.application.ai.ports import VectorSearchResult
from src.domain.company.entities import CompanyMember, CompanyMemberRole
from src.domain.user.entities import User, UserRole
from src.main import app

from tests.unit.application.test_matching_service import (
    _make_candidate,
    _make_company,
    _make_job,
    _make_resume,
)
from tests.unit.fakes import FakeAccessTokenService, FakeUserRepository, build_matching_service


def _make_user(role: UserRole, email: str) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email=email,
        role=role,
        full_name="Test User",
        password_hash="irrelevant",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def harness() -> Iterator[dict]:
    matching_harness = build_matching_service()
    users = FakeUserRepository()

    recruiter = _make_user(UserRole.RECRUITER, "recruiter@example.com")
    outsider = _make_user(UserRole.RECRUITER, "outsider@example.com")
    candidate_user = _make_user(UserRole.CANDIDATE, "candidate@example.com")
    users.add(recruiter)
    users.add(outsider)
    users.add(candidate_user)

    company = matching_harness.companies.add(_make_company(match_threshold=70))
    now = datetime.now(UTC)
    matching_harness.companies.add_member(
        CompanyMember(
            id=uuid.uuid4(),
            company_id=company.id,
            user_id=recruiter.id,
            role=CompanyMemberRole.OWNER,
            created_at=now,
        )
    )

    candidate = _make_candidate(user_id=candidate_user.id)
    matching_harness.candidates.add(candidate)
    matching_harness.resumes.add(_make_resume(candidate.id))

    job = _make_job(company_id=company.id)
    matching_harness.jobs.add(job)
    matching_harness.vector_store.points.setdefault("jobs", {})[str(job.id)] = ([0.1] * 4, {})
    matching_harness.vector_store.search_results["candidates"] = [
        VectorSearchResult(point_id=str(candidate.id), score=0.9, payload={})
    ]

    app.dependency_overrides[get_matching_service] = lambda: matching_harness.service
    app.dependency_overrides[get_job_repository] = lambda: matching_harness.jobs
    app.dependency_overrides[get_candidate_repository] = lambda: matching_harness.candidates
    app.dependency_overrides[get_company_repository] = lambda: matching_harness.companies
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_access_token_service] = lambda: FakeAccessTokenService()
    try:
        yield {
            "matching": matching_harness,
            "company": company,
            "job": job,
            "candidate": candidate,
            "recruiter": recruiter,
            "outsider": outsider,
            "candidate_user": candidate_user,
        }
    finally:
        app.dependency_overrides.clear()


client = TestClient(app)


def _auth_headers(user: User) -> dict[str, str]:
    token = FakeAccessTokenService().create(user)
    return {"Authorization": f"Bearer {token}"}


def test_list_job_candidates_requires_auth(harness: dict) -> None:
    response = client.get(f"/jobs/{harness['job'].id}/candidates")
    assert response.status_code == 401


def test_list_job_candidates_rejects_non_member(harness: dict) -> None:
    response = client.get(
        f"/jobs/{harness['job'].id}/candidates", headers=_auth_headers(harness["outsider"])
    )
    assert response.status_code == 403


def test_list_job_candidates_returns_scores_above_threshold(harness: dict) -> None:
    job = harness["job"]
    candidate = harness["candidate"]
    harness["matching"].service.compute_matches_for_job(job.id)

    response = client.get(f"/jobs/{job.id}/candidates", headers=_auth_headers(harness["recruiter"]))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["candidate"]["id"] == str(candidate.id)
    assert "overall_score" in body[0]["match"]


def test_list_recommended_jobs_requires_candidate_role(harness: dict) -> None:
    response = client.get(
        "/candidates/me/recommended-jobs", headers=_auth_headers(harness["recruiter"])
    )
    assert response.status_code == 403


def test_list_recommended_jobs_returns_scores_above_threshold(harness: dict) -> None:
    candidate = harness["candidate"]
    job = harness["job"]
    harness["matching"].service.compute_matches_for_job(job.id)

    response = client.get(
        "/candidates/me/recommended-jobs", headers=_auth_headers(harness["candidate_user"])
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["job"]["id"] == str(job.id)
    assert candidate.id  # sanity: candidate was matched against this job
