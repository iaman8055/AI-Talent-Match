import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from src.api.deps import (
    get_access_token_service,
    get_application_repository,
    get_application_service,
    get_candidate_repository,
    get_company_repository,
    get_job_repository,
    get_match_score_repository,
    get_user_repository,
)
from src.domain.company.entities import CompanyMember, CompanyMemberRole
from src.domain.user.entities import User, UserRole
from src.main import app

from tests.unit.application.test_matching_service import _make_candidate, _make_company, _make_job
from tests.unit.fakes import (
    ApplicationServiceHarness,
    FakeAccessTokenService,
    FakeMatchScoreRepository,
    build_application_service,
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
    app_harness: ApplicationServiceHarness = build_application_service()
    match_scores = FakeMatchScoreRepository()

    recruiter = _make_user(UserRole.RECRUITER, "recruiter@example.com")
    outsider = _make_user(UserRole.RECRUITER, "outsider@example.com")
    candidate_user = _make_user(UserRole.CANDIDATE, "candidate@example.com")
    candidate_without_profile = _make_user(UserRole.CANDIDATE, "noprofile@example.com")
    app_harness.users.add(recruiter)
    app_harness.users.add(outsider)
    app_harness.users.add(candidate_user)
    app_harness.users.add(candidate_without_profile)

    company = app_harness.companies.add(_make_company())
    now = datetime.now(UTC)
    app_harness.companies.add_member(
        CompanyMember(
            id=uuid.uuid4(),
            company_id=company.id,
            user_id=recruiter.id,
            role=CompanyMemberRole.OWNER,
            created_at=now,
        )
    )

    candidate = app_harness.candidates.add(_make_candidate(user_id=candidate_user.id))
    job = app_harness.jobs.add(_make_job(company_id=company.id))

    app.dependency_overrides[get_application_service] = lambda: app_harness.service
    app.dependency_overrides[get_application_repository] = lambda: app_harness.applications
    app.dependency_overrides[get_job_repository] = lambda: app_harness.jobs
    app.dependency_overrides[get_candidate_repository] = lambda: app_harness.candidates
    app.dependency_overrides[get_company_repository] = lambda: app_harness.companies
    app.dependency_overrides[get_user_repository] = lambda: app_harness.users
    app.dependency_overrides[get_match_score_repository] = lambda: match_scores
    app.dependency_overrides[get_access_token_service] = lambda: FakeAccessTokenService()
    try:
        yield {
            "app": app_harness,
            "match_scores": match_scores,
            "company": company,
            "job": job,
            "candidate": candidate,
            "recruiter": recruiter,
            "outsider": outsider,
            "candidate_user": candidate_user,
            "candidate_without_profile": candidate_without_profile,
        }
    finally:
        app.dependency_overrides.clear()


client = TestClient(app)


def _auth_headers(user: User) -> dict[str, str]:
    token = FakeAccessTokenService().create(user)
    return {"Authorization": f"Bearer {token}"}


def test_candidate_detail_requires_auth(harness: dict) -> None:
    response = client.get(f"/jobs/{harness['job'].id}/candidates/{harness['candidate'].id}")
    assert response.status_code == 401


def test_candidate_detail_rejects_non_member(harness: dict) -> None:
    response = client.get(
        f"/jobs/{harness['job'].id}/candidates/{harness['candidate'].id}",
        headers=_auth_headers(harness["outsider"]),
    )
    assert response.status_code == 403


def test_candidate_detail_returns_candidate_without_match_or_application(harness: dict) -> None:
    response = client.get(
        f"/jobs/{harness['job'].id}/candidates/{harness['candidate'].id}",
        headers=_auth_headers(harness["recruiter"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidate"]["id"] == str(harness["candidate"].id)
    assert body["match"] is None
    assert body["application"] is None
    assert body["matched_skills"] == harness["job"].required_skills
    assert body["missing_skills"] == []


def test_candidate_detail_404_for_unknown_candidate(harness: dict) -> None:
    response = client.get(
        f"/jobs/{harness['job'].id}/candidates/{uuid.uuid4()}",
        headers=_auth_headers(harness["recruiter"]),
    )
    assert response.status_code == 404


def test_candidate_detail_includes_application_once_invited(harness: dict) -> None:
    job = harness["job"]
    candidate = harness["candidate"]
    invite_response = client.post(
        f"/jobs/{job.id}/invite",
        json={"candidate_id": str(candidate.id)},
        headers=_auth_headers(harness["recruiter"]),
    )
    assert invite_response.status_code == 201

    response = client.get(
        f"/jobs/{job.id}/candidates/{candidate.id}", headers=_auth_headers(harness["recruiter"])
    )
    assert response.status_code == 200
    assert response.json()["application"]["status"] == "invited"


def test_invite_candidate_rejects_non_member(harness: dict) -> None:
    response = client.post(
        f"/jobs/{harness['job'].id}/invite",
        json={"candidate_id": str(harness["candidate"].id)},
        headers=_auth_headers(harness["outsider"]),
    )
    assert response.status_code == 403


def test_invite_candidate_creates_application(harness: dict) -> None:
    job = harness["job"]
    candidate = harness["candidate"]
    response = client.post(
        f"/jobs/{job.id}/invite",
        json={"candidate_id": str(candidate.id)},
        headers=_auth_headers(harness["recruiter"]),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "invited"
    assert body["candidate_id"] == str(candidate.id)
    assert len(harness["app"].email_sender.sent) == 1


def test_invite_already_applied_candidate_returns_conflict(harness: dict) -> None:
    job = harness["job"]
    candidate = harness["candidate"]
    harness["app"].service.apply_to_job(candidate.id, job.id)

    response = client.post(
        f"/jobs/{job.id}/invite",
        json={"candidate_id": str(candidate.id)},
        headers=_auth_headers(harness["recruiter"]),
    )
    assert response.status_code == 409


def test_list_job_applications_returns_invited_candidate(harness: dict) -> None:
    job = harness["job"]
    candidate = harness["candidate"]
    client.post(
        f"/jobs/{job.id}/invite",
        json={"candidate_id": str(candidate.id)},
        headers=_auth_headers(harness["recruiter"]),
    )

    response = client.get(
        f"/jobs/{job.id}/applications", headers=_auth_headers(harness["recruiter"])
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["candidate_id"] == str(candidate.id)


def test_apply_to_job_requires_candidate_role(harness: dict) -> None:
    response = client.post(
        "/applications",
        json={"job_id": str(harness["job"].id)},
        headers=_auth_headers(harness["recruiter"]),
    )
    assert response.status_code == 403


def test_apply_to_job_requires_candidate_profile(harness: dict) -> None:
    response = client.post(
        "/applications",
        json={"job_id": str(harness["job"].id)},
        headers=_auth_headers(harness["candidate_without_profile"]),
    )
    assert response.status_code == 404


def test_apply_to_job_creates_application(harness: dict) -> None:
    response = client.post(
        "/applications",
        json={"job_id": str(harness["job"].id)},
        headers=_auth_headers(harness["candidate_user"]),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "applied"


def test_list_my_applications_returns_own_applications(harness: dict) -> None:
    client.post(
        "/applications",
        json={"job_id": str(harness["job"].id)},
        headers=_auth_headers(harness["candidate_user"]),
    )

    response = client.get("/applications", headers=_auth_headers(harness["candidate_user"]))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["job"]["id"] == str(harness["job"].id)
    assert body[0]["application"]["status"] == "applied"


def test_list_my_applications_empty_without_profile(harness: dict) -> None:
    response = client.get(
        "/applications", headers=_auth_headers(harness["candidate_without_profile"])
    )
    assert response.status_code == 200
    assert response.json() == []


class TestPipelineTransitionRoutes:
    def _create_applied(self, harness: dict) -> str:
        response = client.post(
            "/applications",
            json={"job_id": str(harness["job"].id)},
            headers=_auth_headers(harness["candidate_user"]),
        )
        return str(response.json()["id"])

    def test_screen_then_interview_then_offer(self, harness: dict) -> None:
        application_id = self._create_applied(harness)
        headers = _auth_headers(harness["recruiter"])

        screen_resp = client.post(f"/applications/{application_id}/screen", headers=headers)
        assert screen_resp.status_code == 200
        assert screen_resp.json()["status"] == "screening"

        interview_resp = client.post(f"/applications/{application_id}/interview", headers=headers)
        assert interview_resp.status_code == 200
        assert interview_resp.json()["status"] == "interview"

        offer_resp = client.post(f"/applications/{application_id}/offer", headers=headers)
        assert offer_resp.status_code == 200
        assert offer_resp.json()["status"] == "offer"

    def test_reject_from_applied(self, harness: dict) -> None:
        application_id = self._create_applied(harness)
        response = client.post(
            f"/applications/{application_id}/reject", headers=_auth_headers(harness["recruiter"])
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_invalid_transition_returns_conflict(self, harness: dict) -> None:
        application_id = self._create_applied(harness)
        response = client.post(
            f"/applications/{application_id}/interview",
            headers=_auth_headers(harness["recruiter"]),
        )
        assert response.status_code == 409

    def test_transition_rejects_non_member(self, harness: dict) -> None:
        application_id = self._create_applied(harness)
        response = client.post(
            f"/applications/{application_id}/screen", headers=_auth_headers(harness["outsider"])
        )
        assert response.status_code == 403

    def test_transition_requires_auth(self, harness: dict) -> None:
        application_id = self._create_applied(harness)
        response = client.post(f"/applications/{application_id}/screen")
        assert response.status_code == 401
