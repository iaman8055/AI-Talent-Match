import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.domain.company.entities import Company, CompanyInvite, CompanyMember, CompanyMemberRole


class CreateCompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class UpdateCompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class InviteMemberRequest(BaseModel):
    email: EmailStr
    role: CompanyMemberRole = CompanyMemberRole.MEMBER


class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    usage_counters: dict[str, int]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, company: Company) -> "CompanyResponse":
        return cls(
            id=company.id,
            name=company.name,
            slug=company.slug,
            plan=company.plan,
            usage_counters=company.usage_counters,
            created_at=company.created_at,
            updated_at=company.updated_at,
        )


class CompanyMemberResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    user_id: uuid.UUID
    role: CompanyMemberRole
    created_at: datetime

    @classmethod
    def from_entity(cls, member: CompanyMember) -> "CompanyMemberResponse":
        return cls(
            id=member.id,
            company_id=member.company_id,
            user_id=member.user_id,
            role=member.role,
            created_at=member.created_at,
        )


class CompanyInviteResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    email: str
    role: CompanyMemberRole
    expires_at: datetime
    created_at: datetime

    @classmethod
    def from_entity(cls, invite: CompanyInvite) -> "CompanyInviteResponse":
        return cls(
            id=invite.id,
            company_id=invite.company_id,
            email=invite.email,
            role=invite.role,
            expires_at=invite.expires_at,
            created_at=invite.created_at,
        )
