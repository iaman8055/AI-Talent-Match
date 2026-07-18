import uuid
from dataclasses import dataclass
from typing import Protocol

from src.domain.company.entities import CompanyInvite
from src.domain.user.entities import User


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


@dataclass
class AccessTokenClaims:
    user_id: uuid.UUID
    role: str


class AccessTokenService(Protocol):
    def create(self, user: User) -> str: ...

    def decode(self, token: str) -> AccessTokenClaims:
        """Raises ValueError if the token is missing, malformed, or expired."""
        ...


class EmailSender(Protocol):
    def send_verification_email(self, user: User, raw_token: str) -> None: ...

    def send_password_reset_email(self, user: User, raw_token: str) -> None: ...

    def send_invite_email(
        self, invite: CompanyInvite, company_name: str, raw_token: str
    ) -> None: ...


@dataclass
class GoogleUserInfo:
    sub: str
    email: str
    full_name: str
    email_verified: bool


class GoogleOAuthClient(Protocol):
    def exchange_code(self, code: str) -> GoogleUserInfo:
        """Raises ValueError if the code is invalid or the exchange fails."""
        ...
