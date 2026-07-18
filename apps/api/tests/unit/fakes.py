import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.application.auth.ports import AccessTokenClaims, GoogleOAuthClient, GoogleUserInfo
from src.application.auth.service import AuthService
from src.application.company.service import CompanyService
from src.domain.company.entities import Company, CompanyInvite, CompanyMember
from src.domain.user.entities import EmailVerificationToken, PasswordResetToken, RefreshToken, User


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, User] = {}

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def get_by_google_sub(self, sub: str) -> User | None:
        return next((u for u in self._by_id.values() if u.oauth_google_sub == sub), None)

    def add(self, user: User) -> User:
        self._by_id[user.id] = user
        return user

    def update(self, user: User) -> User:
        self._by_id[user.id] = user
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, RefreshToken] = {}

    def add(self, token: RefreshToken) -> RefreshToken:
        self._by_id[token.id] = token
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self._by_id.values() if t.token_hash == token_hash), None)

    def revoke(self, token_id: uuid.UUID, replaced_by_id: uuid.UUID | None = None) -> None:
        token = self._by_id.get(token_id)
        if token is not None:
            token.revoked_at = datetime.now(UTC)
            if replaced_by_id is not None:
                token.replaced_by_id = replaced_by_id

    def revoke_family(self, family_id: uuid.UUID) -> None:
        for token in self._by_id.values():
            if token.family_id == family_id and token.revoked_at is None:
                token.revoked_at = datetime.now(UTC)

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        for token in self._by_id.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = datetime.now(UTC)


class FakeEmailVerificationTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, EmailVerificationToken] = {}

    def add(self, token: EmailVerificationToken) -> EmailVerificationToken:
        self._by_id[token.id] = token
        return token

    def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return next((t for t in self._by_id.values() if t.token_hash == token_hash), None)

    def mark_used(self, token_id: uuid.UUID) -> None:
        token = self._by_id.get(token_id)
        if token is not None:
            token.used_at = datetime.now(UTC)


class FakePasswordResetTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, PasswordResetToken] = {}

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        self._by_id[token.id] = token
        return token

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return next((t for t in self._by_id.values() if t.token_hash == token_hash), None)

    def mark_used(self, token_id: uuid.UUID) -> None:
        token = self._by_id.get(token_id)
        if token is not None:
            token.used_at = datetime.now(UTC)


class FakeCompanyRepository:
    def __init__(self) -> None:
        self._companies: dict[uuid.UUID, Company] = {}
        self._members: dict[uuid.UUID, CompanyMember] = {}
        self._invites: dict[uuid.UUID, CompanyInvite] = {}

    def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        return self._companies.get(company_id)

    def get_by_slug(self, slug: str) -> Company | None:
        return next((c for c in self._companies.values() if c.slug == slug), None)

    def add(self, company: Company) -> Company:
        self._companies[company.id] = company
        return company

    def update(self, company: Company) -> Company:
        self._companies[company.id] = company
        return company

    def add_member(self, member: CompanyMember) -> CompanyMember:
        self._members[member.id] = member
        return member

    def get_member(self, company_id: uuid.UUID, user_id: uuid.UUID) -> CompanyMember | None:
        return next(
            (
                m
                for m in self._members.values()
                if m.company_id == company_id and m.user_id == user_id
            ),
            None,
        )

    def list_members(self, company_id: uuid.UUID) -> list[CompanyMember]:
        return [m for m in self._members.values() if m.company_id == company_id]

    def add_invite(self, invite: CompanyInvite) -> CompanyInvite:
        self._invites[invite.id] = invite
        return invite

    def get_invite_by_hash(self, token_hash: str) -> CompanyInvite | None:
        return next((i for i in self._invites.values() if i.token_hash == token_hash), None)

    def mark_invite_accepted(self, invite_id: uuid.UUID) -> None:
        invite = self._invites.get(invite_id)
        if invite is not None:
            invite.accepted_at = datetime.now(UTC)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeAccessTokenService:
    def create(self, user: User) -> str:
        return f"access:{user.id}:{user.role.value}"

    def decode(self, token: str) -> AccessTokenClaims:
        try:
            _, raw_id, role = token.split(":")
            return AccessTokenClaims(user_id=uuid.UUID(raw_id), role=role)
        except ValueError as exc:
            raise ValueError("Invalid access token") from exc


@dataclass
class FakeEmailSender:
    sent: list[tuple[str, str, str]] = field(default_factory=list)

    def send_verification_email(self, user: User, raw_token: str) -> None:
        self.sent.append(("verification", user.email, raw_token))

    def send_password_reset_email(self, user: User, raw_token: str) -> None:
        self.sent.append(("password_reset", user.email, raw_token))

    def send_invite_email(self, invite: CompanyInvite, company_name: str, raw_token: str) -> None:
        self.sent.append(("invite", invite.email, raw_token))


@dataclass
class FakeGoogleOAuthClient:
    user_info: GoogleUserInfo | None = None
    error: str | None = None

    def exchange_code(self, code: str) -> GoogleUserInfo:
        if self.error is not None:
            raise ValueError(self.error)
        assert self.user_info is not None
        return self.user_info


@dataclass
class AuthServiceHarness:
    service: AuthService
    users: FakeUserRepository
    refresh_tokens: FakeRefreshTokenRepository
    companies: FakeCompanyRepository
    email_sender: FakeEmailSender


def build_auth_service(
    google_oauth_client: GoogleOAuthClient | None = None,
    refresh_token_expire_days: int = 30,
) -> AuthServiceHarness:
    users = FakeUserRepository()
    refresh_tokens = FakeRefreshTokenRepository()
    companies = FakeCompanyRepository()
    email_sender = FakeEmailSender()

    service = AuthService(
        user_repo=users,
        refresh_token_repo=refresh_tokens,
        email_verification_repo=FakeEmailVerificationTokenRepository(),
        password_reset_repo=FakePasswordResetTokenRepository(),
        company_repo=companies,
        password_hasher=FakePasswordHasher(),
        access_token_service=FakeAccessTokenService(),
        email_sender=email_sender,
        refresh_token_expire_days=refresh_token_expire_days,
        google_oauth_client=google_oauth_client,
    )
    return AuthServiceHarness(
        service=service,
        users=users,
        refresh_tokens=refresh_tokens,
        companies=companies,
        email_sender=email_sender,
    )


@dataclass
class CompanyServiceHarness:
    service: CompanyService
    companies: FakeCompanyRepository
    email_sender: FakeEmailSender


def build_company_service() -> CompanyServiceHarness:
    companies = FakeCompanyRepository()
    email_sender = FakeEmailSender()
    service = CompanyService(companies, email_sender)
    return CompanyServiceHarness(service=service, companies=companies, email_sender=email_sender)
