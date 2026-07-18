import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.application.auth.ports import (
    AccessTokenService,
    EmailSender,
    GoogleOAuthClient,
    PasswordHasher,
)
from src.application.auth.service import AuthService
from src.application.company.service import CompanyService
from src.core.config import Settings, get_settings
from src.domain.company.entities import CompanyMember, CompanyMemberRole
from src.domain.company.repository import CompanyRepository
from src.domain.user.entities import User, UserRole
from src.domain.user.repository import (
    EmailVerificationTokenRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from src.infrastructure.db.repositories import (
    SqlAlchemyCompanyRepository,
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from src.infrastructure.db.session import get_db
from src.infrastructure.notifications.email.celery_email_sender import CeleryEmailSender
from src.infrastructure.oauth.google_oauth_client import (
    GoogleOAuthClient as ConcreteGoogleOAuthClient,
)
from src.infrastructure.security.jwt_service import JWTTokenService
from src.infrastructure.security.password_hasher import Argon2PasswordHasher

_bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_refresh_token_repository(db: Session = Depends(get_db)) -> RefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(db)


def get_email_verification_repository(
    db: Session = Depends(get_db),
) -> EmailVerificationTokenRepository:
    return SqlAlchemyEmailVerificationTokenRepository(db)


def get_password_reset_repository(db: Session = Depends(get_db)) -> PasswordResetTokenRepository:
    return SqlAlchemyPasswordResetTokenRepository(db)


def get_company_repository(db: Session = Depends(get_db)) -> CompanyRepository:
    return SqlAlchemyCompanyRepository(db)


def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_access_token_service(settings: Settings = Depends(get_settings)) -> AccessTokenService:
    return JWTTokenService(settings.jwt_secret_key, settings.jwt_access_token_expire_minutes)


def get_email_sender(settings: Settings = Depends(get_settings)) -> EmailSender:
    return CeleryEmailSender(settings.frontend_url)


def get_google_oauth_client(settings: Settings = Depends(get_settings)) -> GoogleOAuthClient | None:
    if not (
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_oauth_redirect_uri
    ):
        return None
    return ConcreteGoogleOAuthClient(
        settings.google_client_id, settings.google_client_secret, settings.google_oauth_redirect_uri
    )


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    email_verification_repo: EmailVerificationTokenRepository = Depends(
        get_email_verification_repository
    ),
    password_reset_repo: PasswordResetTokenRepository = Depends(get_password_reset_repository),
    company_repo: CompanyRepository = Depends(get_company_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    access_token_service: AccessTokenService = Depends(get_access_token_service),
    email_sender: EmailSender = Depends(get_email_sender),
    google_oauth_client: GoogleOAuthClient | None = Depends(get_google_oauth_client),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        email_verification_repo=email_verification_repo,
        password_reset_repo=password_reset_repo,
        company_repo=company_repo,
        password_hasher=password_hasher,
        access_token_service=access_token_service,
        email_sender=email_sender,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
        google_oauth_client=google_oauth_client,
    )


def get_company_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    email_sender: EmailSender = Depends(get_email_sender),
) -> CompanyService:
    return CompanyService(company_repo, email_sender)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
    access_token_service: AccessTokenService = Depends(get_access_token_service),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        claims = access_token_service.decode(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token"
        ) from exc

    user = user_repo.get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token")

    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return current_user

    return dependency


def require_company_role(*roles: CompanyMemberRole) -> Callable[..., CompanyMember]:
    def dependency(
        company_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        company_repo: CompanyRepository = Depends(get_company_repository),
    ) -> CompanyMember:
        member = company_repo.get_member(company_id, current_user.id)
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this company")
        if roles and member.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Insufficient permissions in this company"
            )
        return member

    return dependency
