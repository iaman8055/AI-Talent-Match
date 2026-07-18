from fastapi import APIRouter, Depends, status

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
from src.domain.user.entities import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)
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
def login(
    body: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    user, tokens = auth_service.login(body.email, body.password)
    return AuthResponse.from_result(user, tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    body: RefreshRequest, auth_service: AuthService = Depends(get_auth_service)
) -> TokenResponse:
    tokens = auth_service.refresh(body.refresh_token)
    return TokenResponse.from_token_pair(tokens)


@router.post("/verify-email", status_code=status.HTTP_204_NO_CONTENT)
def verify_email(
    body: VerifyEmailRequest, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    auth_service.verify_email(body.token)


@router.post("/request-password-reset", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(
    body: RequestPasswordResetRequest, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    auth_service.request_password_reset(body.email)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    body: ResetPasswordRequest, auth_service: AuthService = Depends(get_auth_service)
) -> None:
    auth_service.reset_password(body.token, body.new_password)


@router.post("/oauth/google", response_model=AuthResponse)
def oauth_google(
    body: GoogleOAuthRequest, auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    user, tokens = auth_service.oauth_google_login(body.code)
    return AuthResponse.from_result(user, tokens)


@router.post("/accept-invite", response_model=AuthResponse)
def accept_invite(
    body: AcceptInviteRequest, auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    user, tokens = auth_service.accept_invite(body.token, body.password, body.full_name)
    return AuthResponse.from_result(user, tokens)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.from_entity(current_user)
