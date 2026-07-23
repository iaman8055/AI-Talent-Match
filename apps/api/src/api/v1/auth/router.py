from fastapi import APIRouter, Depends, Request, status

from src.api.deps import get_auth_service, get_current_user
from src.api.v1.auth.schemas import (
    AcceptInviteRequest,
    AuthResponse,
    GoogleOAuthRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RequestPasswordResetRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from src.application.auth.service import AuthService
from src.core.rate_limit import limiter
from src.domain.user.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def register(
    request: Request,
    body: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user, tokens = auth_service.register(
        email=body.email,
        password=body.password,
        role=body.role,
        full_name=body.full_name,
        company_name=body.company_name,
    )
    return AuthResponse.from_result(user, tokens)


@router.post("/login", response_model=AuthResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user, tokens = auth_service.login(body.email, body.password)
    return AuthResponse.from_result(user, tokens)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("30/minute")
def refresh(
    request: Request,
    body: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    tokens = auth_service.refresh(body.refresh_token)
    return TokenResponse.from_token_pair(tokens)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(
    body: VerifyEmailRequest, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    auth_service.verify_email(body.token)


@router.post("/request-password-reset", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
def request_password_reset(
    request: Request,
    body: RequestPasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    auth_service.request_password_reset(body.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    auth_service.reset_password(body.token, body.new_password)


@router.post("/oauth/google", response_model=AuthResponse)
@limiter.limit("10/minute")
def oauth_google(
    request: Request,
    body: GoogleOAuthRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user, tokens = auth_service.oauth_google_login(body.code)
    return AuthResponse.from_result(user, tokens)


@router.post("/accept-invite", response_model=AuthResponse)
@limiter.limit("10/minute")
def accept_invite(
    request: Request,
    body: AcceptInviteRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    user, tokens = auth_service.accept_invite(body.token, body.password, body.full_name)
    return AuthResponse.from_result(user, tokens)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_entity(current_user)
