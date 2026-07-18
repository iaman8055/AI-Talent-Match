import uuid
from datetime import UTC, datetime, timedelta

import pytest
from src.application.auth.ports import GoogleUserInfo
from src.application.company.service import CompanyService
from src.application.exceptions import (
    ConflictError,
    InvalidCredentialsError,
    InvalidTokenError,
    ServiceUnavailableError,
    ValidationError,
)
from src.domain.company.entities import CompanyMemberRole
from src.domain.user.entities import RefreshToken, User, UserRole

from tests.unit.fakes import FakeGoogleOAuthClient, build_auth_service


def _register_candidate(harness, email: str = "candidate@example.com") -> tuple[User, object]:
    return harness.service.register(
        email=email,
        password="correct horse battery staple",
        role=UserRole.CANDIDATE,
        full_name="Cand Idate",
        company_name=None,
    )


class TestRegister:
    def test_candidate_registration_issues_tokens_and_sends_verification_email(self) -> None:
        harness = build_auth_service()

        user, tokens = _register_candidate(harness)

        assert user.role == UserRole.CANDIDATE
        assert user.email_verified_at is None
        assert tokens.access_token
        assert tokens.refresh_token
        assert harness.email_sender.sent[0][0] == "verification"

    def test_recruiter_registration_creates_company_and_owner_membership(self) -> None:
        harness = build_auth_service()

        user, _tokens = harness.service.register(
            email="owner@acme.com",
            password="correct horse battery staple",
            role=UserRole.RECRUITER,
            full_name="Owner Person",
            company_name="Acme Inc",
        )

        companies = list(harness.companies._companies.values())
        assert len(companies) == 1
        member = harness.companies.get_member(companies[0].id, user.id)
        assert member is not None
        assert member.role == CompanyMemberRole.OWNER

    def test_recruiter_registration_without_company_name_is_rejected(self) -> None:
        harness = build_auth_service()

        with pytest.raises(ValidationError):
            harness.service.register(
                email="owner@acme.com",
                password="correct horse battery staple",
                role=UserRole.RECRUITER,
                full_name="Owner Person",
                company_name=None,
            )

    def test_cannot_self_register_as_admin(self) -> None:
        harness = build_auth_service()

        with pytest.raises(ValidationError):
            harness.service.register(
                email="admin@example.com",
                password="correct horse battery staple",
                role=UserRole.ADMIN,
                full_name="Admin",
                company_name=None,
            )

    def test_duplicate_email_is_rejected(self) -> None:
        harness = build_auth_service()
        _register_candidate(harness)

        with pytest.raises(ConflictError):
            _register_candidate(harness)


class TestLogin:
    def test_login_succeeds_with_correct_password(self) -> None:
        harness = build_auth_service()
        _register_candidate(harness)

        user, tokens = harness.service.login(
            "candidate@example.com", "correct horse battery staple"
        )

        assert user.email == "candidate@example.com"
        assert tokens.access_token

    def test_login_fails_with_wrong_password(self) -> None:
        harness = build_auth_service()
        _register_candidate(harness)

        with pytest.raises(InvalidCredentialsError):
            harness.service.login("candidate@example.com", "wrong password")

    def test_login_fails_for_unknown_email(self) -> None:
        harness = build_auth_service()

        with pytest.raises(InvalidCredentialsError):
            harness.service.login("nobody@example.com", "whatever")

    def test_login_fails_for_oauth_only_account(self) -> None:
        harness = build_auth_service(
            google_oauth_client=FakeGoogleOAuthClient(
                user_info=GoogleUserInfo(
                    sub="google-1", email="g@example.com", full_name="G", email_verified=True
                )
            )
        )
        harness.service.oauth_google_login("some-code")

        with pytest.raises(InvalidCredentialsError):
            harness.service.login("g@example.com", "anything")


class TestRefresh:
    def test_refresh_rotates_token_and_revokes_old_one(self) -> None:
        harness = build_auth_service()
        _user, tokens = _register_candidate(harness)

        new_tokens = harness.service.refresh(tokens.refresh_token)

        assert new_tokens.refresh_token != tokens.refresh_token
        old = harness.refresh_tokens.get_by_hash(_hash(tokens.refresh_token))
        assert old is not None
        assert old.revoked_at is not None

    def test_reusing_a_rotated_token_revokes_the_whole_family(self) -> None:
        harness = build_auth_service()
        _user, tokens = _register_candidate(harness)

        new_tokens = harness.service.refresh(tokens.refresh_token)

        with pytest.raises(InvalidTokenError):
            harness.service.refresh(tokens.refresh_token)

        # The token issued by the first (legitimate) rotation should now be
        # revoked too, since the whole family was burned.
        with pytest.raises(InvalidTokenError):
            harness.service.refresh(new_tokens.refresh_token)

    def test_expired_refresh_token_is_rejected(self) -> None:
        harness = build_auth_service()
        user, _tokens = _register_candidate(harness)

        raw_token = "expired-raw-token"
        expired = RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=_hash(raw_token),
            family_id=uuid.uuid4(),
            expires_at=datetime.now(UTC) - timedelta(days=1),
            revoked_at=None,
            replaced_by_id=None,
            created_at=datetime.now(UTC) - timedelta(days=31),
        )
        harness.refresh_tokens.add(expired)

        with pytest.raises(InvalidTokenError):
            harness.service.refresh(raw_token)

    def test_unknown_refresh_token_is_rejected(self) -> None:
        harness = build_auth_service()

        with pytest.raises(InvalidTokenError):
            harness.service.refresh("not-a-real-token")


class TestPasswordReset:
    def test_request_reset_does_not_leak_account_existence(self) -> None:
        harness = build_auth_service()

        harness.service.request_password_reset("nobody@example.com")

        assert harness.email_sender.sent == []

    def test_reset_password_changes_password_and_revokes_sessions(self) -> None:
        harness = build_auth_service()
        user, tokens = _register_candidate(harness)

        harness.service.request_password_reset(user.email)
        _kind, _email, raw_token = harness.email_sender.sent[-1]

        harness.service.reset_password(raw_token, "a brand new password")

        # Old sessions are dead.
        with pytest.raises(InvalidTokenError):
            harness.service.refresh(tokens.refresh_token)

        # New password works, old one doesn't.
        harness.service.login(user.email, "a brand new password")
        with pytest.raises(InvalidCredentialsError):
            harness.service.login(user.email, "correct horse battery staple")

    def test_reset_password_rejects_invalid_token(self) -> None:
        harness = build_auth_service()

        with pytest.raises(InvalidTokenError):
            harness.service.reset_password("bogus", "a brand new password")


class TestVerifyEmail:
    def test_verify_email_marks_user_verified(self) -> None:
        harness = build_auth_service()
        user, _tokens = _register_candidate(harness)
        _kind, _email, raw_token = harness.email_sender.sent[0]

        harness.service.verify_email(raw_token)

        stored = harness.users.get_by_id(user.id)
        assert stored is not None
        assert stored.email_verified_at is not None

    def test_verify_email_rejects_invalid_token(self) -> None:
        harness = build_auth_service()

        with pytest.raises(InvalidTokenError):
            harness.service.verify_email("bogus")


class TestGoogleOAuth:
    def test_new_google_user_is_created_as_candidate(self) -> None:
        harness = build_auth_service(
            google_oauth_client=FakeGoogleOAuthClient(
                user_info=GoogleUserInfo(
                    sub="google-42",
                    email="new@example.com",
                    full_name="New Person",
                    email_verified=True,
                )
            )
        )

        user, tokens = harness.service.oauth_google_login("code")

        assert user.role == UserRole.CANDIDATE
        assert user.oauth_google_sub == "google-42"
        assert user.email_verified_at is not None
        assert tokens.access_token

    def test_google_login_links_existing_email_password_account(self) -> None:
        harness = build_auth_service(
            google_oauth_client=FakeGoogleOAuthClient(
                user_info=GoogleUserInfo(
                    sub="google-42",
                    email="candidate@example.com",
                    full_name="Cand Idate",
                    email_verified=True,
                )
            )
        )
        existing, _tokens = _register_candidate(harness)

        linked, _tokens2 = harness.service.oauth_google_login("code")

        assert linked.id == existing.id
        assert linked.oauth_google_sub == "google-42"

    def test_oauth_not_configured_raises_service_unavailable(self) -> None:
        harness = build_auth_service(google_oauth_client=None)

        with pytest.raises(ServiceUnavailableError):
            harness.service.oauth_google_login("code")


class TestAcceptInvite:
    def test_accept_invite_creates_recruiter_and_membership(self) -> None:
        harness = build_auth_service()
        owner, _tokens = harness.service.register(
            email="owner@acme.com",
            password="correct horse battery staple",
            role=UserRole.RECRUITER,
            full_name="Owner",
            company_name="Acme",
        )
        company = next(iter(harness.companies._companies.values()))
        company_service = CompanyService(harness.companies, harness.email_sender)
        company_service.invite_member(
            company.id, "new-recruiter@acme.com", CompanyMemberRole.MEMBER, owner.id
        )
        _kind, _email, raw_token = harness.email_sender.sent[-1]

        new_user, tokens = harness.service.accept_invite(
            raw_token, "another password", "New Recruiter"
        )

        assert new_user.role == UserRole.RECRUITER
        member = harness.companies.get_member(company.id, new_user.id)
        assert member is not None
        assert member.role == CompanyMemberRole.MEMBER
        assert tokens.access_token

    def test_accept_invite_rejects_invalid_token(self) -> None:
        harness = build_auth_service()

        with pytest.raises(InvalidTokenError):
            harness.service.accept_invite("bogus", "password", "Name")


def _hash(raw_token: str) -> str:
    from src.application.tokens import hash_token

    return hash_token(raw_token)
