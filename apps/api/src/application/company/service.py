import re
import uuid
from datetime import UTC, datetime, timedelta

from src.application.auth.ports import EmailSender
from src.application.exceptions import NotFoundError
from src.application.tokens import generate_raw_token, hash_token
from src.domain.company.entities import Company, CompanyInvite, CompanyMember, CompanyMemberRole
from src.domain.company.repository import CompanyRepository

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")
DEFAULT_MATCH_THRESHOLD = 70


def generate_unique_slug(company_repo: CompanyRepository, name: str) -> str:
    base_slug = _SLUG_INVALID_CHARS.sub("-", name.lower()).strip("-") or "company"
    slug = base_slug
    suffix = 2
    while company_repo.get_by_slug(slug) is not None:
        slug = f"{base_slug}-{suffix}"
        suffix += 1
    return slug


class CompanyService:
    def __init__(self, company_repo: CompanyRepository, email_sender: EmailSender) -> None:
        self._companies = company_repo
        self._email_sender = email_sender

    def create_company(self, name: str, owner_user_id: uuid.UUID) -> Company:
        now = datetime.now(UTC)
        company = Company(
            id=uuid.uuid4(),
            name=name,
            slug=generate_unique_slug(self._companies, name),
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

    def get_company(self, company_id: uuid.UUID) -> Company:
        company = self._companies.get_by_id(company_id)
        if company is None:
            raise NotFoundError("Company not found")
        return company

    def update_company(
        self,
        company_id: uuid.UUID,
        name: str | None = None,
        match_threshold: int | None = None,
    ) -> Company:
        company = self.get_company(company_id)
        if name is not None:
            company.name = name
        if match_threshold is not None:
            company.match_threshold = match_threshold
        company.updated_at = datetime.now(UTC)
        return self._companies.update(company)

    def list_members(self, company_id: uuid.UUID) -> list[CompanyMember]:
        return self._companies.list_members(company_id)

    def invite_member(
        self,
        company_id: uuid.UUID,
        email: str,
        role: CompanyMemberRole,
        invited_by_user_id: uuid.UUID,
    ) -> CompanyInvite:
        company = self.get_company(company_id)

        raw_token = generate_raw_token()
        now = datetime.now(UTC)
        invite = CompanyInvite(
            id=uuid.uuid4(),
            company_id=company_id,
            email=email,
            role=role,
            token_hash=hash_token(raw_token),
            invited_by_user_id=invited_by_user_id,
            expires_at=now + timedelta(days=7),
            accepted_at=None,
            created_at=now,
        )
        invite = self._companies.add_invite(invite)
        self._email_sender.send_invite_email(invite, company.name, raw_token)
        return invite
