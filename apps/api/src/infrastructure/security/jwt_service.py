import uuid
from datetime import UTC, datetime, timedelta

import jwt

from src.application.auth.ports import AccessTokenClaims
from src.domain.user.entities import User


class JWTTokenService:
    def __init__(self, secret_key: str, expire_minutes: int) -> None:
        self._secret_key = secret_key
        self._expire_minutes = expire_minutes

    def create(self, user: User) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": str(user.id),
            "role": user.role.value,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self._expire_minutes),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self._secret_key, algorithm="HS256")

    def decode(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=["HS256"])
        except jwt.PyJWTError as exc:
            raise ValueError("Invalid or expired access token") from exc

        if payload.get("type") != "access":
            raise ValueError("Invalid token type")

        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise ValueError("Invalid access token subject") from exc

        role = payload.get("role")
        if not isinstance(role, str):
            raise ValueError("Invalid access token role")

        return AccessTokenClaims(user_id=user_id, role=role)
