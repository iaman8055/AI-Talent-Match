import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CompanyMemberRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class Company:
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    usage_counters: dict[str, int]
    match_threshold: int
    created_at: datetime
    updated_at: datetime


@dataclass
class CompanyMember:
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    role: CompanyMemberRole
    created_at: datetime


@dataclass
class CompanyInvite:
    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    role: CompanyMemberRole
    token_hash: str
    invited_by_user_id: uuid.UUID
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
