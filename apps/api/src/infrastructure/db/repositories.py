import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.domain.company.entities import Company, CompanyInvite, CompanyMember, CompanyMemberRole
from src.domain.user.entities import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserRole,
)
from src.infrastructure.db.models import (
    CompanyInviteModel,
    CompanyMemberModel,
    CompanyModel,
    EmailVerificationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserModel,
)


def _user_to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        role=UserRole(model.role),
        full_name=model.full_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        email_verified_at=model.email_verified_at,
        oauth_google_sub=model.oauth_google_sub,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _user_to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalars(select(UserModel).where(UserModel.email == email)).first()
        return _user_to_entity(model) if model else None

    def get_by_google_sub(self, sub: str) -> User | None:
        model = self._session.scalars(
            select(UserModel).where(UserModel.oauth_google_sub == sub)
        ).first()
        return _user_to_entity(model) if model else None

    def add(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            role=user.role.value,
            full_name=user.full_name,
            password_hash=user.password_hash,
            is_active=user.is_active,
            email_verified_at=user.email_verified_at,
            oauth_google_sub=user.oauth_google_sub,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        self._session.flush()
        return _user_to_entity(model)

    def update(self, user: User) -> User:
        model = self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User {user.id} not found")
        model.email = user.email
        model.role = user.role.value
        model.full_name = user.full_name
        model.password_hash = user.password_hash
        model.is_active = user.is_active
        model.email_verified_at = user.email_verified_at
        model.oauth_google_sub = user.oauth_google_sub
        model.updated_at = user.updated_at
        self._session.flush()
        return _user_to_entity(model)


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: RefreshToken) -> RefreshToken:
        model = RefreshTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            family_id=token.family_id,
            expires_at=token.expires_at,
            revoked_at=token.revoked_at,
            replaced_by_id=token.replaced_by_id,
            created_at=token.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        model = self._session.scalars(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        ).first()
        if model is None:
            return None
        return RefreshToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            family_id=model.family_id,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
            replaced_by_id=model.replaced_by_id,
            created_at=model.created_at,
        )

    def revoke(self, token_id: uuid.UUID, replaced_by_id: uuid.UUID | None = None) -> None:
        model = self._session.get(RefreshTokenModel, token_id)
        if model is None:
            return
        model.revoked_at = datetime.now(UTC)
        if replaced_by_id is not None:
            model.replaced_by_id = replaced_by_id
        self._session.flush()

    def revoke_family(self, family_id: uuid.UUID) -> None:
        self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id, RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )


class SqlAlchemyEmailVerificationTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: EmailVerificationToken) -> EmailVerificationToken:
        model = EmailVerificationTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return token

    def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        model = self._session.scalars(
            select(EmailVerificationTokenModel).where(
                EmailVerificationTokenModel.token_hash == token_hash
            )
        ).first()
        if model is None:
            return None
        return EmailVerificationToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            used_at=model.used_at,
            created_at=model.created_at,
        )

    def mark_used(self, token_id: uuid.UUID) -> None:
        model = self._session.get(EmailVerificationTokenModel, token_id)
        if model is not None:
            model.used_at = datetime.now(UTC)
            self._session.flush()


class SqlAlchemyPasswordResetTokenRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        model = PasswordResetTokenModel(
            id=token.id,
            user_id=token.user_id,
            token_hash=token.token_hash,
            expires_at=token.expires_at,
            used_at=token.used_at,
            created_at=token.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return token

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        model = self._session.scalars(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        ).first()
        if model is None:
            return None
        return PasswordResetToken(
            id=model.id,
            user_id=model.user_id,
            token_hash=model.token_hash,
            expires_at=model.expires_at,
            used_at=model.used_at,
            created_at=model.created_at,
        )

    def mark_used(self, token_id: uuid.UUID) -> None:
        model = self._session.get(PasswordResetTokenModel, token_id)
        if model is not None:
            model.used_at = datetime.now(UTC)
            self._session.flush()


def _company_to_entity(model: CompanyModel) -> Company:
    return Company(
        id=model.id,
        name=model.name,
        slug=model.slug,
        plan=model.plan,
        usage_counters=model.usage_counters,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _member_to_entity(model: CompanyMemberModel) -> CompanyMember:
    return CompanyMember(
        id=model.id,
        company_id=model.company_id,
        user_id=model.user_id,
        role=CompanyMemberRole(model.role),
        created_at=model.created_at,
    )


def _invite_to_entity(model: CompanyInviteModel) -> CompanyInvite:
    return CompanyInvite(
        id=model.id,
        company_id=model.company_id,
        email=model.email,
        role=CompanyMemberRole(model.role),
        token_hash=model.token_hash,
        invited_by_user_id=model.invited_by_user_id,
        expires_at=model.expires_at,
        accepted_at=model.accepted_at,
        created_at=model.created_at,
    )


class SqlAlchemyCompanyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        model = self._session.get(CompanyModel, company_id)
        return _company_to_entity(model) if model else None

    def get_by_slug(self, slug: str) -> Company | None:
        model = self._session.scalars(select(CompanyModel).where(CompanyModel.slug == slug)).first()
        return _company_to_entity(model) if model else None

    def add(self, company: Company) -> Company:
        model = CompanyModel(
            id=company.id,
            name=company.name,
            slug=company.slug,
            plan=company.plan,
            usage_counters=company.usage_counters,
            created_at=company.created_at,
            updated_at=company.updated_at,
        )
        self._session.add(model)
        self._session.flush()
        return _company_to_entity(model)

    def update(self, company: Company) -> Company:
        model = self._session.get(CompanyModel, company.id)
        if model is None:
            raise ValueError(f"Company {company.id} not found")
        model.name = company.name
        model.plan = company.plan
        model.usage_counters = company.usage_counters
        model.updated_at = company.updated_at
        self._session.flush()
        return _company_to_entity(model)

    def add_member(self, member: CompanyMember) -> CompanyMember:
        model = CompanyMemberModel(
            id=member.id,
            company_id=member.company_id,
            user_id=member.user_id,
            role=member.role.value,
            created_at=member.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return _member_to_entity(model)

    def get_member(self, company_id: uuid.UUID, user_id: uuid.UUID) -> CompanyMember | None:
        model = self._session.scalars(
            select(CompanyMemberModel).where(
                CompanyMemberModel.company_id == company_id,
                CompanyMemberModel.user_id == user_id,
            )
        ).first()
        return _member_to_entity(model) if model else None

    def list_members(self, company_id: uuid.UUID) -> list[CompanyMember]:
        models = self._session.scalars(
            select(CompanyMemberModel).where(CompanyMemberModel.company_id == company_id)
        ).all()
        return [_member_to_entity(model) for model in models]

    def add_invite(self, invite: CompanyInvite) -> CompanyInvite:
        model = CompanyInviteModel(
            id=invite.id,
            company_id=invite.company_id,
            email=invite.email,
            role=invite.role.value,
            token_hash=invite.token_hash,
            invited_by_user_id=invite.invited_by_user_id,
            expires_at=invite.expires_at,
            accepted_at=invite.accepted_at,
            created_at=invite.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return _invite_to_entity(model)

    def get_invite_by_hash(self, token_hash: str) -> CompanyInvite | None:
        model = self._session.scalars(
            select(CompanyInviteModel).where(CompanyInviteModel.token_hash == token_hash)
        ).first()
        return _invite_to_entity(model) if model else None

    def mark_invite_accepted(self, invite_id: uuid.UUID) -> None:
        model = self._session.get(CompanyInviteModel, invite_id)
        if model is not None:
            model.accepted_at = datetime.now(UTC)
            self._session.flush()
