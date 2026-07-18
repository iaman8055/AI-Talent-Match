import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.application.auth.service import TokenPair
from src.domain.user.entities import User, UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole
    full_name: str = Field(min_length=1, max_length=200)
    company_name: str | None = Field(default=None, min_length=1, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class RequestPasswordResetRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class GoogleOAuthRequest(BaseModel):
    code: str


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    full_name: str
    is_active: bool
    email_verified: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            role=user.role,
            full_name=user.full_name,
            is_active=user.is_active,
            email_verified=user.email_verified_at is not None,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_token_pair(cls, tokens: TokenPair) -> "TokenResponse":
        return cls(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse

    @classmethod
    def from_result(cls, user: User, tokens: TokenPair) -> "AuthResponse":
        return cls(
            user=UserResponse.from_entity(user), tokens=TokenResponse.from_token_pair(tokens)
        )
