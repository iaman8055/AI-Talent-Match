from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from src.api.deps import get_access_token_service, get_auth_service, get_user_repository
from src.application.auth.service import AuthService
from src.main import app

from tests.unit.fakes import FakeAccessTokenService, build_auth_service


@pytest.fixture
def harness() -> Iterator[object]:
    harness = build_auth_service()

    def _get_auth_service() -> AuthService:
        return harness.service

    def _get_user_repository() -> object:
        return harness.users

    def _get_access_token_service() -> FakeAccessTokenService:
        return FakeAccessTokenService()

    app.dependency_overrides[get_auth_service] = _get_auth_service
    app.dependency_overrides[get_user_repository] = _get_user_repository
    app.dependency_overrides[get_access_token_service] = _get_access_token_service
    try:
        yield harness
    finally:
        app.dependency_overrides.clear()


client = TestClient(app)


def test_register_returns_created_user_and_tokens(harness: object) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "correct horse battery staple",
            "role": "candidate",
            "full_name": "Cand Idate",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "candidate@example.com"
    assert body["tokens"]["access_token"]


def test_duplicate_register_returns_409(harness: object) -> None:
    payload = {
        "email": "candidate@example.com",
        "password": "correct horse battery staple",
        "role": "candidate",
        "full_name": "Cand Idate",
    }
    client.post("/auth/register", json=payload)

    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409


def test_login_with_wrong_password_returns_401(harness: object) -> None:
    client.post(
        "/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "correct horse battery staple",
            "role": "candidate",
            "full_name": "Cand Idate",
        },
    )

    response = client.post(
        "/auth/login", json={"email": "candidate@example.com", "password": "wrong"}
    )

    assert response.status_code == 401


def test_me_without_token_returns_401(harness: object) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_with_valid_token_returns_current_user(harness: object) -> None:
    register_response = client.post(
        "/auth/register",
        json={
            "email": "candidate@example.com",
            "password": "correct horse battery staple",
            "role": "candidate",
            "full_name": "Cand Idate",
        },
    )
    access_token = register_response.json()["tokens"]["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "candidate@example.com"


def test_recruiter_registration_rejects_missing_company_name(harness: object) -> None:
    response = client.post(
        "/auth/register",
        json={
            "email": "owner@acme.com",
            "password": "correct horse battery staple",
            "role": "recruiter",
            "full_name": "Owner",
        },
    )

    assert response.status_code == 422
