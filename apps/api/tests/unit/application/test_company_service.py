import uuid

import pytest
from src.application.exceptions import NotFoundError
from src.domain.company.entities import CompanyMemberRole

from tests.unit.fakes import build_company_service


class TestCreateCompany:
    def test_create_company_adds_owner_membership(self) -> None:
        harness = build_company_service()
        owner_id = uuid.uuid4()

        company = harness.service.create_company("Acme Inc", owner_id)

        assert company.slug == "acme-inc"
        member = harness.companies.get_member(company.id, owner_id)
        assert member is not None
        assert member.role == CompanyMemberRole.OWNER

    def test_slug_collisions_are_disambiguated(self) -> None:
        harness = build_company_service()

        first = harness.service.create_company("Acme Inc", uuid.uuid4())
        second = harness.service.create_company("Acme Inc", uuid.uuid4())

        assert first.slug == "acme-inc"
        assert second.slug == "acme-inc-2"

    def test_new_company_defaults_to_70_percent_threshold(self) -> None:
        harness = build_company_service()

        company = harness.service.create_company("Acme Inc", uuid.uuid4())

        assert company.match_threshold == 70


class TestGetAndUpdateCompany:
    def test_get_unknown_company_raises_not_found(self) -> None:
        harness = build_company_service()

        with pytest.raises(NotFoundError):
            harness.service.get_company(uuid.uuid4())

    def test_update_company_changes_name(self) -> None:
        harness = build_company_service()
        company = harness.service.create_company("Acme Inc", uuid.uuid4())

        updated = harness.service.update_company(company.id, "Acme Corp")

        assert updated.name == "Acme Corp"
        assert harness.service.get_company(company.id).name == "Acme Corp"

    def test_update_company_changes_match_threshold_only(self) -> None:
        harness = build_company_service()
        company = harness.service.create_company("Acme Inc", uuid.uuid4())

        updated = harness.service.update_company(company.id, match_threshold=85)

        assert updated.match_threshold == 85
        assert updated.name == "Acme Inc"  # untouched


class TestMembersAndInvites:
    def test_list_members_returns_only_this_companys_members(self) -> None:
        harness = build_company_service()
        company_a = harness.service.create_company("Acme", uuid.uuid4())
        company_b = harness.service.create_company("Globex", uuid.uuid4())

        members_a = harness.service.list_members(company_a.id)
        members_b = harness.service.list_members(company_b.id)

        assert len(members_a) == 1
        assert len(members_b) == 1
        assert members_a[0].company_id == company_a.id

    def test_invite_member_sends_email_with_token(self) -> None:
        harness = build_company_service()
        owner_id = uuid.uuid4()
        company = harness.service.create_company("Acme", owner_id)

        invite = harness.service.invite_member(
            company.id, "new@acme.com", CompanyMemberRole.MEMBER, owner_id
        )

        assert invite.email == "new@acme.com"
        assert invite.accepted_at is None
        assert harness.email_sender.sent[-1][0] == "invite"
        assert harness.email_sender.sent[-1][1] == "new@acme.com"
