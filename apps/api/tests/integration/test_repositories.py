import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session
from src.domain.company.entities import Company, CompanyMember, CompanyMemberRole
from src.domain.user.entities import User, UserRole
from src.infrastructure.db.repositories import SqlAlchemyCompanyRepository, SqlAlchemyUserRepository


def _make_user(email: str = "test@example.com") -> User:
    now = datetime.now(UTC)
    return User(
        id=uuid.uuid4(),
        email=email,
        role=UserRole.CANDIDATE,
        full_name="Test User",
        password_hash="hashed:password",
        is_active=True,
        email_verified_at=None,
        oauth_google_sub=None,
        created_at=now,
        updated_at=now,
    )


class TestSqlAlchemyUserRepository:
    def test_add_and_get_by_id_round_trips(self, db_session: Session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        user = _make_user()

        repo.add(user)
        fetched = repo.get_by_id(user.id)

        assert fetched is not None
        assert fetched.email == user.email
        assert fetched.role == UserRole.CANDIDATE

    def test_get_by_email(self, db_session: Session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        repo.add(_make_user(email="findme@example.com"))

        fetched = repo.get_by_email("findme@example.com")

        assert fetched is not None
        assert fetched.email == "findme@example.com"

    def test_get_by_email_returns_none_when_missing(self, db_session: Session) -> None:
        repo = SqlAlchemyUserRepository(db_session)

        assert repo.get_by_email("nobody@example.com") is None

    def test_update_persists_changes(self, db_session: Session) -> None:
        repo = SqlAlchemyUserRepository(db_session)
        user = repo.add(_make_user())

        user.full_name = "Updated Name"
        user.is_active = False
        repo.update(user)

        fetched = repo.get_by_id(user.id)
        assert fetched is not None
        assert fetched.full_name == "Updated Name"
        assert fetched.is_active is False


class TestSqlAlchemyCompanyRepository:
    def test_add_company_and_member_round_trip(self, db_session: Session) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        company_repo = SqlAlchemyCompanyRepository(db_session)
        owner = user_repo.add(_make_user(email="owner@example.com"))

        now = datetime.now(UTC)
        company = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="Acme Inc",
                slug="acme-inc",
                plan="free",
                usage_counters={},
                created_at=now,
                updated_at=now,
            )
        )
        company_repo.add_member(
            CompanyMember(
                id=uuid.uuid4(),
                company_id=company.id,
                user_id=owner.id,
                role=CompanyMemberRole.OWNER,
                created_at=now,
            )
        )

        fetched_company = company_repo.get_by_slug("acme-inc")
        member = company_repo.get_member(company.id, owner.id)

        assert fetched_company is not None
        assert fetched_company.name == "Acme Inc"
        assert member is not None
        assert member.role == CompanyMemberRole.OWNER

    def test_list_members_scopes_to_company(self, db_session: Session) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        company_repo = SqlAlchemyCompanyRepository(db_session)
        now = datetime.now(UTC)

        company_a = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="A",
                slug="company-a",
                plan="free",
                usage_counters={},
                created_at=now,
                updated_at=now,
            )
        )
        company_b = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="B",
                slug="company-b",
                plan="free",
                usage_counters={},
                created_at=now,
                updated_at=now,
            )
        )
        user_a = user_repo.add(_make_user(email="a@example.com"))
        user_b = user_repo.add(_make_user(email="b@example.com"))
        company_repo.add_member(
            CompanyMember(
                id=uuid.uuid4(),
                company_id=company_a.id,
                user_id=user_a.id,
                role=CompanyMemberRole.OWNER,
                created_at=now,
            )
        )
        company_repo.add_member(
            CompanyMember(
                id=uuid.uuid4(),
                company_id=company_b.id,
                user_id=user_b.id,
                role=CompanyMemberRole.OWNER,
                created_at=now,
            )
        )

        members_a = company_repo.list_members(company_a.id)

        assert len(members_a) == 1
        assert members_a[0].user_id == user_a.id
