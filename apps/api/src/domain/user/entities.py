import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class UserRole(StrEnum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


@dataclass
class User:
    id: uuid.UUID
    email: str
    role: UserRole
    full_name: str
    password_hash: str | None
    is_active: bool
    email_verified_at: datetime | None
    oauth_google_sub: str | None
    created_at: datetime
    updated_at: datetime


@dataclass
class RefreshToken:
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    family_id: uuid.UUID
    expires_at: datetime
    revoked_at: datetime | None
    replaced_by_id: uuid.UUID | None
    created_at: datetime


@dataclass
class EmailVerificationToken:
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime


@dataclass
class PasswordResetToken:
    id: uuid.UUID
    user_id: uuid.UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime
