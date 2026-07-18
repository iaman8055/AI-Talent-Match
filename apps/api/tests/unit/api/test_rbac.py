import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from src.api.deps import require_company_role, require_roles
from src.domain.company.entities import CompanyMember, CompanyMemberRole
from src.domain.user.entities import User, UserRole

from tests.unit.fakes import FakeCompanyRepository


def _make_user(role: UserRole) -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        role=role,
        full_name="Some User",
        password_hash="irrelevant",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )


class TestRequireRoles:
    def test_allows_matching_role(self) -> None:
        user = _make_user(UserRole.RECRUITER)
        dependency = require_roles(UserRole.RECRUITER, UserRole.ADMIN)

        assert dependency(current_user=user) is user

    def test_rejects_non_matching_role(self) -> None:
        user = _make_user(UserRole.CANDIDATE)
        dependency = require_roles(UserRole.RECRUITER)

        with pytest.raises(HTTPException) as exc_info:
            dependency(current_user=user)
        assert exc_info.value.status_code == 403


class TestRequireCompanyRole:
    def test_allows_member_with_matching_role(self) -> None:
        companies = FakeCompanyRepository()
        user = _make_user(UserRole.RECRUITER)
        company_id = uuid.uuid4()
        member = CompanyMember(
            id=uuid.uuid4(),
            company_id=company_id,
            user_id=user.id,
            role=CompanyMemberRole.OWNER,
            created_at=datetime.now(UTC),
        )
        companies.add_member(member)
        dependency = require_company_role(CompanyMemberRole.OWNER, CompanyMemberRole.ADMIN)

        result = dependency(company_id=company_id, current_user=user, company_repo=companies)

        assert result.role == CompanyMemberRole.OWNER

    def test_rejects_non_member(self) -> None:
        companies = FakeCompanyRepository()
        user = _make_user(UserRole.RECRUITER)
        dependency = require_company_role()

        with pytest.raises(HTTPException) as exc_info:
            dependency(company_id=uuid.uuid4(), current_user=user, company_repo=companies)
        assert exc_info.value.status_code == 403

    def test_rejects_member_with_insufficient_role(self) -> None:
        companies = FakeCompanyRepository()
        user = _make_user(UserRole.RECRUITER)
        company_id = uuid.uuid4()
        companies.add_member(
            CompanyMember(
                id=uuid.uuid4(),
                company_id=company_id,
                user_id=user.id,
                role=CompanyMemberRole.MEMBER,
                created_at=datetime.now(UTC),
            )
        )
        dependency = require_company_role(CompanyMemberRole.OWNER, CompanyMemberRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            dependency(company_id=company_id, current_user=user, company_repo=companies)
        assert exc_info.value.status_code == 403

    def test_no_roles_specified_allows_any_member(self) -> None:
        companies = FakeCompanyRepository()
        user = _make_user(UserRole.RECRUITER)
        company_id = uuid.uuid4()
        companies.add_member(
            CompanyMember(
                id=uuid.uuid4(),
                company_id=company_id,
                user_id=user.id,
                role=CompanyMemberRole.MEMBER,
                created_at=datetime.now(UTC),
            )
        )
        dependency = require_company_role()

        result = dependency(company_id=company_id, current_user=user, company_repo=companies)

        assert result.role == CompanyMemberRole.MEMBER
