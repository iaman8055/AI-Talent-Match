import uuid
from datetime import UTC, datetime

import jwt
import pytest
from src.domain.user.entities import User, UserRole
from src.infrastructure.security.jwt_service import JWTTokenService


def _make_user() -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        role=UserRole.CANDIDATE,
        full_name="Test User",
        password_hash="irrelevant",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )


def test_create_and_decode_round_trip() -> None:
    service = JWTTokenService(secret_key="test-secret-that-is-long-enough-1234", expire_minutes=15)
    user = _make_user()

    token = service.create(user)
    claims = service.decode(token)

    assert claims.user_id == user.id
    assert claims.role == UserRole.CANDIDATE.value


def test_decode_rejects_token_signed_with_a_different_secret() -> None:
    service = JWTTokenService(secret_key="test-secret-that-is-long-enough-1234", expire_minutes=15)
    other_service = JWTTokenService(
        secret_key="a-different-secret-that-is-also-long-enough-5678", expire_minutes=15
    )
    token = service.create(_make_user())

    with pytest.raises(ValueError):
        other_service.decode(token)


def test_decode_rejects_expired_token() -> None:
    service = JWTTokenService(secret_key="test-secret-that-is-long-enough-1234", expire_minutes=-1)
    token = service.create(_make_user())

    with pytest.raises(ValueError):
        service.decode(token)


def test_decode_rejects_non_access_token_type() -> None:
    service = JWTTokenService(secret_key="test-secret-that-is-long-enough-1234", expire_minutes=15)
    payload = {
        "sub": str(uuid.uuid4()),
        "role": "candidate",
        "type": "refresh",
    }
    token = jwt.encode(payload, "test-secret-that-is-long-enough-1234", algorithm="HS256")

    with pytest.raises(ValueError):
        service.decode(token)
