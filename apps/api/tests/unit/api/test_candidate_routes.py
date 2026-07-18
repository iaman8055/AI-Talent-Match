import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from src.api.deps import get_access_token_service, get_candidate_service, get_user_repository
from src.domain.user.entities import User, UserRole
from src.main import app

from tests.unit.fakes import FakeAccessTokenService, FakeUserRepository, build_candidate_service

_VALID_PDF_BYTES = b"%PDF-1.4\nfake pdf content for tests\n"


def _make_candidate_user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email="candidate@example.com",
        role=UserRole.CANDIDATE,
        full_name="Cand Idate",
        password_hash="irrelevant",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def harness() -> Iterator[object]:
    candidate_harness = build_candidate_service()
    user = _make_candidate_user()
    users = FakeUserRepository()
    users.add(user)

    app.dependency_overrides[get_candidate_service] = lambda: candidate_harness.service
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_access_token_service] = lambda: FakeAccessTokenService()
    try:
        yield {"candidate": candidate_harness, "user": user}
    finally:
        app.dependency_overrides.clear()


client = TestClient(app)


def _auth_headers(user: User) -> dict[str, str]:
    token = FakeAccessTokenService().create(user)
    return {"Authorization": f"Bearer {token}"}


def test_get_my_profile_requires_auth(harness: dict) -> None:
    response = client.get("/candidates/me")
    assert response.status_code == 401


def test_get_my_profile_creates_and_returns_profile(harness: dict) -> None:
    user = harness["user"]

    response = client.get("/candidates/me", headers=_auth_headers(user))

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.id)


def test_update_profile(harness: dict) -> None:
    user = harness["user"]

    response = client.patch(
        "/candidates/me/profile",
        json={"full_name": "New Name", "skills": ["Python", "SQL"]},
        headers=_auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "New Name"
    assert body["skills"] == ["Python", "SQL"]


def test_upload_resume_rejects_unsupported_type(harness: dict) -> None:
    user = harness["user"]

    response = client.post(
        "/candidates/me/resume",
        files={"file": ("resume.txt", b"not a real resume", "text/plain")},
        headers=_auth_headers(user),
    )

    assert response.status_code == 422


def test_upload_and_list_resume(harness: dict) -> None:
    user = harness["user"]

    upload_response = client.post(
        "/candidates/me/resume",
        files={"file": ("resume.pdf", _VALID_PDF_BYTES, "application/pdf")},
        headers=_auth_headers(user),
    )
    assert upload_response.status_code == 201
    resume_id = upload_response.json()["id"]

    list_response = client.get("/candidates/me/resume", headers=_auth_headers(user))
    assert list_response.status_code == 200
    assert [r["id"] for r in list_response.json()] == [resume_id]

    detail_response = client.get(f"/candidates/me/resume/{resume_id}", headers=_auth_headers(user))
    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "pending"

    download_response = client.get(
        f"/candidates/me/resume/{resume_id}/download-url", headers=_auth_headers(user)
    )
    assert download_response.status_code == 200
    assert "url" in download_response.json()


def test_get_resume_not_found_for_unknown_id(harness: dict) -> None:
    user = harness["user"]

    response = client.get(f"/candidates/me/resume/{uuid.uuid4()}", headers=_auth_headers(user))

    assert response.status_code == 404


def test_recruiter_cannot_access_candidate_routes(harness: dict) -> None:
    now = datetime.now(UTC)
    recruiter = User(
        id=uuid.uuid4(),
        email="recruiter@example.com",
        role=UserRole.RECRUITER,
        full_name="Rec Ruiter",
        password_hash="irrelevant",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )
    users: FakeUserRepository = app.dependency_overrides[get_user_repository]()
    users.add(recruiter)

    response = client.get("/candidates/me", headers=_auth_headers(recruiter))

    assert response.status_code == 403
