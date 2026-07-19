import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.application.auth.ports import (
    AccessTokenService,
    EmailSender,
    GoogleOAuthClient,
    PasswordHasher,
)
from src.application.company.service import DEFAULT_MATCH_THRESHOLD, generate_unique_slug
from src.application.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    InvalidTokenError,
    ServiceUnavailableError,
    ValidationError,
)
from src.application.tokens import generate_raw_token, hash_token
from src.domain.company.entities import Company, CompanyMember, CompanyMemberRole
from src.domain.company.repository import CompanyRepository
from src.domain.user.entities import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserRole,
)
from src.domain.user.repository import (
    EmailVerificationTokenRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        refresh_token_repo: RefreshTokenRepository,
        email_verification_repo: EmailVerificationTokenRepository,
        password_reset_repo: PasswordResetTokenRepository,
        company_repo: CompanyRepository,
        password_hasher: PasswordHasher,
        access_token_service: AccessTokenService,
        email_sender: EmailSender,
        refresh_token_expire_days: int,
        google_oauth_client: GoogleOAuthClient | None = None,
    ) -> None:
        self._users = user_repo
        self._refresh_tokens = refresh_token_repo
        self._email_verification_tokens = email_verification_repo
        self._password_reset_tokens = password_reset_repo
        self._companies = company_repo
        self._password_hasher = password_hasher
        self._access_tokens = access_token_service
        self._email_sender = email_sender
        self._refresh_token_expire_days = refresh_token_expire_days
        self._google_oauth_client = google_oauth_client

    def register(
        self,
        email: str,
        password: str,
        role: UserRole,
        full_name: str,
        company_name: str | None,
    ) -> tuple[User, TokenPair]:
        if role == UserRole.ADMIN:
            raise ValidationError("Cannot self-register as admin")
        if role == UserRole.RECRUITER and not company_name:
            raise ValidationError("company_name is required when registering as a recruiter")
        if self._users.get_by_email(email) is not None:
            raise ConflictError("Email is already registered")

        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=email,
            role=role,
            full_name=full_name,
            password_hash=self._password_hasher.hash(password),
            is_active=True,
            email_verified_at=None,
            oauth_google_sub=None,
            created_at=now,
            updated_at=now,
        )
        user = self._users.add(user)

        if role == UserRole.RECRUITER:
            assert company_name is not None
            self._create_company_for_owner(company_name, user.id)

        self._issue_email_verification(user)
        return user, self._issue_tokens(user)

    def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = self._users.get_by_email(email)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError("Invalid email or password")
        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InvalidCredentialsError("Account is inactive")

        return user, self._issue_tokens(user)

    def refresh(self, raw_refresh_token: str) -> TokenPair:
        token_hash = hash_token(raw_refresh_token)
        existing = self._refresh_tokens.get_by_hash(token_hash)
        if existing is None:
            raise InvalidTokenError("Invalid refresh token")

        if existing.revoked_at is not None:
            # The same refresh token was presented twice: either a client double-submit
            # or theft/replay of a stolen token. Revoking the whole family is the standard
            # mitigation — it also cheaply covers the double-submit case since the
            # legitimate client already has the token this rotated into.
            self._refresh_tokens.revoke_family(existing.family_id)
            raise InvalidTokenError("Refresh token already used; session revoked")

        if existing.expires_at < datetime.now(UTC):
            raise InvalidTokenError("Refresh token expired")

        user = self._users.get_by_id(existing.user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError("Invalid refresh token")

        new_token, new_raw_token = self._create_refresh_token(user.id, existing.family_id)
        self._refresh_tokens.revoke(existing.id, replaced_by_id=new_token.id)

        access_token = self._access_tokens.create(user)
        return TokenPair(access_token=access_token, refresh_token=new_raw_token)

    def verify_email(self, raw_token: str) -> None:
        token_hash = hash_token(raw_token)
        record = self._email_verification_tokens.get_by_hash(token_hash)
        if record is None or record.used_at is not None or record.expires_at < datetime.now(UTC):
            raise InvalidTokenError("Invalid or expired verification token")

        user = self._users.get_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("Invalid or expired verification token")

        user.email_verified_at = datetime.now(UTC)
        user.updated_at = user.email_verified_at
        self._users.update(user)
        self._email_verification_tokens.mark_used(record.id)

    def request_password_reset(self, email: str) -> None:
        user = self._users.get_by_email(email)
        if user is None or user.password_hash is None:
            return  # Don't reveal whether the account exists or is OAuth-only.

        raw_token = generate_raw_token()
        now = datetime.now(UTC)
        token = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(hours=1),
            used_at=None,
            created_at=now,
        )
        self._password_reset_tokens.add(token)
        self._email_sender.send_password_reset_email(user, raw_token)

    def reset_password(self, raw_token: str, new_password: str) -> None:
        token_hash = hash_token(raw_token)
        record = self._password_reset_tokens.get_by_hash(token_hash)
        if record is None or record.used_at is not None or record.expires_at < datetime.now(UTC):
            raise InvalidTokenError("Invalid or expired reset token")

        user = self._users.get_by_id(record.user_id)
        if user is None:
            raise InvalidTokenError("Invalid or expired reset token")

        user.password_hash = self._password_hasher.hash(new_password)
        user.updated_at = datetime.now(UTC)
        self._users.update(user)
        self._password_reset_tokens.mark_used(record.id)
        # A password reset invalidates every existing session, not just the one that
        # requested it — otherwise a stolen-but-not-yet-expired session survives the reset.
        self._refresh_tokens.revoke_all_for_user(user.id)

    def oauth_google_login(self, code: str) -> tuple[User, TokenPair]:
        if self._google_oauth_client is None:
            raise ServiceUnavailableError("Google OAuth is not configured")

        try:
            info = self._google_oauth_client.exchange_code(code)
        except ValueError as exc:
            raise InvalidTokenError(str(exc)) from exc

        user = self._users.get_by_google_sub(info.sub)
        now = datetime.now(UTC)
        if user is None:
            user = self._users.get_by_email(info.email)
            if user is not None:
                user.oauth_google_sub = info.sub
                if info.email_verified and user.email_verified_at is None:
                    user.email_verified_at = now
                user.updated_at = now
                user = self._users.update(user)
            else:
                user = User(
                    id=uuid.uuid4(),
                    email=info.email,
                    role=UserRole.CANDIDATE,
                    full_name=info.full_name,
                    password_hash=None,
                    is_active=True,
                    email_verified_at=now if info.email_verified else None,
                    oauth_google_sub=info.sub,
                    created_at=now,
                    updated_at=now,
                )
                user = self._users.add(user)

        if not user.is_active:
            raise InvalidCredentialsError("Account is inactive")

        return user, self._issue_tokens(user)

    def accept_invite(
        self, raw_token: str, password: str, full_name: str
    ) -> tuple[User, TokenPair]:
        token_hash = hash_token(raw_token)
        invite = self._companies.get_invite_by_hash(token_hash)
        if (
            invite is None
            or invite.accepted_at is not None
            or invite.expires_at < datetime.now(UTC)
        ):
            raise InvalidTokenError("Invalid or expired invite")

        now = datetime.now(UTC)
        user = self._users.get_by_email(invite.email)
        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=invite.email,
                role=UserRole.RECRUITER,
                full_name=full_name,
                password_hash=self._password_hasher.hash(password),
                is_active=True,
                email_verified_at=now,
                oauth_google_sub=None,
                created_at=now,
                updated_at=now,
            )
            user = self._users.add(user)

        if self._companies.get_member(invite.company_id, user.id) is None:
            self._companies.add_member(
                CompanyMember(
                    id=uuid.uuid4(),
                    company_id=invite.company_id,
                    user_id=user.id,
                    role=invite.role,
                    created_at=now,
                )
            )
        self._companies.mark_invite_accepted(invite.id)

        return user, self._issue_tokens(user)

    def _create_company_for_owner(self, company_name: str, owner_user_id: uuid.UUID) -> Company:
        now = datetime.now(UTC)
        company = Company(
            id=uuid.uuid4(),
            name=company_name,
            slug=generate_unique_slug(self._companies, company_name),
            plan="free",
            usage_counters={},
            match_threshold=DEFAULT_MATCH_THRESHOLD,
            created_at=now,
            updated_at=now,
        )
        company = self._companies.add(company)
        self._companies.add_member(
            CompanyMember(
                id=uuid.uuid4(),
                company_id=company.id,
                user_id=owner_user_id,
                role=CompanyMemberRole.OWNER,
                created_at=now,
            )
        )
        return company

    def _issue_email_verification(self, user: User) -> None:
        raw_token = generate_raw_token()
        now = datetime.now(UTC)
        token = EmailVerificationToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(days=2),
            used_at=None,
            created_at=now,
        )
        self._email_verification_tokens.add(token)
        self._email_sender.send_verification_email(user, raw_token)

    def _create_refresh_token(
        self, user_id: uuid.UUID, family_id: uuid.UUID
    ) -> tuple[RefreshToken, str]:
        raw_token = generate_raw_token()
        now = datetime.now(UTC)
        token = RefreshToken(
            id=uuid.uuid4(),
            user_id=user_id,
            token_hash=hash_token(raw_token),
            family_id=family_id,
            expires_at=now + timedelta(days=self._refresh_token_expire_days),
            revoked_at=None,
            replaced_by_id=None,
            created_at=now,
        )
        stored = self._refresh_tokens.add(token)
        return stored, raw_token

    def _issue_tokens(self, user: User) -> TokenPair:
        family_id = uuid.uuid4()
        _, raw_token = self._create_refresh_token(user.id, family_id)
        access_token = self._access_tokens.create(user)
        return TokenPair(access_token=access_token, refresh_token=raw_token)
