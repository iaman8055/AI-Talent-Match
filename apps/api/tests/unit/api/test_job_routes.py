import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from src.api.deps import (
    get_access_token_service,
    get_company_repository,
    get_job_repository,
    get_job_service,
    get_user_repository,
)
from src.domain.company.entities import Company, CompanyMember, CompanyMemberRole
from src.domain.job.entities import JobProcessingStatus
from src.domain.user.entities import User, UserRole
from src.main import app

from tests.unit.fakes import (
    FakeAccessTokenService,
    FakeCompanyRepository,
    FakeUserRepository,
    build_job_service,
)


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
    job_harness = build_job_service()
    companies = FakeCompanyRepository()
    users = FakeUserRepository()

    recruiter = _make_user(UserRole.RECRUITER, "recruiter@example.com")
    outsider = _make_user(UserRole.RECRUITER, "outsider@example.com")
    candidate = _make_user(UserRole.CANDIDATE, "candidate@example.com")
    users.add(recruiter)
    users.add(outsider)
    users.add(candidate)

    now = datetime.now(UTC)
    company = Company(
        id=uuid.uuid4(),
        name="Acme",
        slug="acme",
        plan="free",
        usage_counters={},
        created_at=now,
        updated_at=now,
    )
    companies.add(company)
    companies.add_member(
        CompanyMember(
            id=uuid.uuid4(),
            company_id=company.id,
            user_id=recruiter.id,
            role=CompanyMemberRole.OWNER,
            created_at=now,
        )
    )

    app.dependency_overrides[get_job_service] = lambda: job_harness.service
    app.dependency_overrides[get_job_repository] = lambda: job_harness.jobs
    app.dependency_overrides[get_company_repository] = lambda: companies
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_access_token_service] = lambda: FakeAccessTokenService()
    try:
        yield {
            "jobs": job_harness,
            "company": company,
            "recruiter": recruiter,
            "outsider": outsider,
            "candidate": candidate,
        }
    finally:
        app.dependency_overrides.clear()


client = TestClient(app)


def _auth_headers(user: User) -> dict[str, str]:
    token = FakeAccessTokenService().create(user)
    return {"Authorization": f"Bearer {token}"}


def test_create_job_requires_auth(harness: dict) -> None:
    response = client.post(
        "/jobs", json={"company_id": str(uuid.uuid4()), "title": "x", "raw_description": "y"}
    )
    assert response.status_code == 401


def test_candidate_cannot_create_job(harness: dict) -> None:
    response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["candidate"]),
    )
    assert response.status_code == 403


def test_non_member_recruiter_cannot_create_job(harness: dict) -> None:
    response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["outsider"]),
    )
    assert response.status_code == 403


def test_create_and_get_job(harness: dict) -> None:
    create_response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )
    assert create_response.status_code == 201
    job_id = create_response.json()["id"]
    assert create_response.json()["lifecycle_status"] == "draft"

    get_response = client.get(f"/jobs/{job_id}", headers=_auth_headers(harness["recruiter"]))
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Engineer"


def test_list_jobs_scoped_to_company(harness: dict) -> None:
    client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )

    response = client.get(
        "/jobs",
        params={"company_id": str(harness["company"].id)},
        headers=_auth_headers(harness["recruiter"]),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_unknown_job_returns_404(harness: dict) -> None:
    response = client.get(f"/jobs/{uuid.uuid4()}", headers=_auth_headers(harness["recruiter"]))
    assert response.status_code == 404


def test_outsider_cannot_access_job(harness: dict) -> None:
    create_response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )
    job_id = create_response.json()["id"]

    response = client.get(f"/jobs/{job_id}", headers=_auth_headers(harness["outsider"]))
    assert response.status_code == 403


def test_update_job(harness: dict) -> None:
    create_response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )
    job_id = create_response.json()["id"]

    response = client.patch(
        f"/jobs/{job_id}",
        json={"salary_min": 100000, "work_mode": "remote"},
        headers=_auth_headers(harness["recruiter"]),
    )

    assert response.status_code == 200
    assert response.json()["salary_min"] == 100000
    assert response.json()["work_mode"] == "remote"


def test_publish_requires_ready_processing_status(harness: dict) -> None:
    create_response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )
    job_id = create_response.json()["id"]

    response = client.post(f"/jobs/{job_id}/publish", headers=_auth_headers(harness["recruiter"]))

    assert response.status_code == 422


def test_publish_close_reopen_lifecycle(harness: dict) -> None:
    create_response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )
    job_id = create_response.json()["id"]
    job = harness["jobs"].jobs.get_by_id(uuid.UUID(job_id))
    job.processing_status = JobProcessingStatus.READY
    harness["jobs"].jobs.update(job)

    publish_response = client.post(
        f"/jobs/{job_id}/publish", headers=_auth_headers(harness["recruiter"])
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["lifecycle_status"] == "published"

    close_response = client.post(
        f"/jobs/{job_id}/close", headers=_auth_headers(harness["recruiter"])
    )
    assert close_response.status_code == 200
    assert close_response.json()["lifecycle_status"] == "closed"

    reopen_response = client.post(
        f"/jobs/{job_id}/reopen", headers=_auth_headers(harness["recruiter"])
    )
    assert reopen_response.status_code == 200
    assert reopen_response.json()["lifecycle_status"] == "published"


def test_delete_draft_job(harness: dict) -> None:
    create_response = client.post(
        "/jobs",
        json={
            "company_id": str(harness["company"].id),
            "title": "Engineer",
            "raw_description": "desc",
        },
        headers=_auth_headers(harness["recruiter"]),
    )
    job_id = create_response.json()["id"]

    response = client.delete(f"/jobs/{job_id}", headers=_auth_headers(harness["recruiter"]))

    assert response.status_code == 204
    assert (
        client.get(f"/jobs/{job_id}", headers=_auth_headers(harness["recruiter"])).status_code
        == 404
    )
