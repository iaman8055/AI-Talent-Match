import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.domain.applications.entities import Application, ApplicationStatus
from src.domain.candidate.entities import (
    Candidate,
    Education,
    Location,
    Resume,
    ResumeStatus,
    WorkExperience,
    WorkMode,
)
from src.domain.company.entities import Company, CompanyInvite, CompanyMember, CompanyMemberRole
from src.domain.job.entities import Job, JobLifecycleStatus, JobProcessingStatus, JobVersion
from src.domain.job.entities import Location as JobLocation
from src.domain.job.entities import WorkMode as JobWorkMode
from src.domain.matching.entities import MatchScore
from src.domain.user.entities import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserRole,
)
from src.infrastructure.db.models import (
    ApplicationModel,
    CandidateModel,
    CompanyInviteModel,
    CompanyMemberModel,
    CompanyModel,
    EmailVerificationTokenModel,
    JobModel,
    JobVersionModel,
    MatchScoreModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    ResumeModel,
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
        match_threshold=model.match_threshold,
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
            match_threshold=company.match_threshold,
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
        model.match_threshold = company.match_threshold
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


def _work_experience_to_json(items: list[WorkExperience]) -> list[dict[str, object]]:
    return [
        {
            "company": item.company,
            "title": item.title,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "end_date": item.end_date.isoformat() if item.end_date else None,
            "description": item.description,
        }
        for item in items
    ]


def _education_to_json(items: list[Education]) -> list[dict[str, object]]:
    return [
        {
            "institution": item.institution,
            "degree": item.degree,
            "field_of_study": item.field_of_study,
            "start_date": item.start_date.isoformat() if item.start_date else None,
            "end_date": item.end_date.isoformat() if item.end_date else None,
        }
        for item in items
    ]


def _candidate_to_entity(model: CandidateModel) -> Candidate:
    return Candidate(
        id=model.id,
        user_id=model.user_id,
        full_name=model.full_name,
        headline=model.headline,
        summary=model.summary,
        skills=model.skills,
        total_experience_years=model.total_experience_years,
        location=Location(
            country=model.location_country,
            region=model.location_region,
            city=model.location_city,
        ),
        desired_salary_min=model.desired_salary_min,
        desired_salary_max=model.desired_salary_max,
        work_mode_preference=(
            WorkMode(model.work_mode_preference) if model.work_mode_preference else None
        ),
        work_experience=[
            WorkExperience(
                company=str(item["company"]),
                title=str(item["title"]),
                start_date=(
                    date.fromisoformat(str(item["start_date"])) if item.get("start_date") else None
                ),
                end_date=(
                    date.fromisoformat(str(item["end_date"])) if item.get("end_date") else None
                ),
                description=str(item["description"]) if item.get("description") else None,
            )
            for item in model.work_experience
        ],
        education=[
            Education(
                institution=str(item["institution"]),
                degree=str(item["degree"]) if item.get("degree") else None,
                field_of_study=str(item["field_of_study"]) if item.get("field_of_study") else None,
                start_date=(
                    date.fromisoformat(str(item["start_date"])) if item.get("start_date") else None
                ),
                end_date=(
                    date.fromisoformat(str(item["end_date"])) if item.get("end_date") else None
                ),
            )
            for item in model.education
        ],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyCandidateRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, candidate_id: uuid.UUID) -> Candidate | None:
        model = self._session.get(CandidateModel, candidate_id)
        return _candidate_to_entity(model) if model else None

    def get_by_user_id(self, user_id: uuid.UUID) -> Candidate | None:
        model = self._session.scalars(
            select(CandidateModel).where(CandidateModel.user_id == user_id)
        ).first()
        return _candidate_to_entity(model) if model else None

    def add(self, candidate: Candidate) -> Candidate:
        model = CandidateModel(
            id=candidate.id,
            user_id=candidate.user_id,
            full_name=candidate.full_name,
            headline=candidate.headline,
            summary=candidate.summary,
            skills=candidate.skills,
            total_experience_years=candidate.total_experience_years,
            location_country=candidate.location.country,
            location_region=candidate.location.region,
            location_city=candidate.location.city,
            desired_salary_min=candidate.desired_salary_min,
            desired_salary_max=candidate.desired_salary_max,
            work_mode_preference=(
                candidate.work_mode_preference.value if candidate.work_mode_preference else None
            ),
            work_experience=_work_experience_to_json(candidate.work_experience),
            education=_education_to_json(candidate.education),
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
        )
        self._session.add(model)
        self._session.flush()
        return _candidate_to_entity(model)

    def update(self, candidate: Candidate) -> Candidate:
        model = self._session.get(CandidateModel, candidate.id)
        if model is None:
            raise ValueError(f"Candidate {candidate.id} not found")
        model.full_name = candidate.full_name
        model.headline = candidate.headline
        model.summary = candidate.summary
        model.skills = candidate.skills
        model.total_experience_years = candidate.total_experience_years
        model.location_country = candidate.location.country
        model.location_region = candidate.location.region
        model.location_city = candidate.location.city
        model.desired_salary_min = candidate.desired_salary_min
        model.desired_salary_max = candidate.desired_salary_max
        model.work_mode_preference = (
            candidate.work_mode_preference.value if candidate.work_mode_preference else None
        )
        model.work_experience = _work_experience_to_json(candidate.work_experience)
        model.education = _education_to_json(candidate.education)
        model.updated_at = candidate.updated_at
        self._session.flush()
        return _candidate_to_entity(model)


def _resume_to_entity(model: ResumeModel) -> Resume:
    return Resume(
        id=model.id,
        candidate_id=model.candidate_id,
        version=model.version,
        s3_key=model.s3_key,
        original_filename=model.original_filename,
        file_type=model.file_type,
        content_type=model.content_type,
        file_size=model.file_size,
        content_hash=model.content_hash,
        status=ResumeStatus(model.status),
        parser_version=model.parser_version,
        error_message=model.error_message,
        uploaded_at=model.uploaded_at,
        parsed_at=model.parsed_at,
    )


class SqlAlchemyResumeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, resume: Resume) -> Resume:
        model = ResumeModel(
            id=resume.id,
            candidate_id=resume.candidate_id,
            version=resume.version,
            s3_key=resume.s3_key,
            original_filename=resume.original_filename,
            file_type=resume.file_type,
            content_type=resume.content_type,
            file_size=resume.file_size,
            content_hash=resume.content_hash,
            status=resume.status.value,
            parser_version=resume.parser_version,
            error_message=resume.error_message,
            uploaded_at=resume.uploaded_at,
            parsed_at=resume.parsed_at,
        )
        self._session.add(model)
        self._session.flush()
        return _resume_to_entity(model)

    def get_by_id(self, resume_id: uuid.UUID) -> Resume | None:
        model = self._session.get(ResumeModel, resume_id)
        return _resume_to_entity(model) if model else None

    def list_by_candidate(self, candidate_id: uuid.UUID) -> list[Resume]:
        models = self._session.scalars(
            select(ResumeModel)
            .where(ResumeModel.candidate_id == candidate_id)
            .order_by(ResumeModel.version.desc())
        ).all()
        return [_resume_to_entity(model) for model in models]

    def get_by_content_hash(self, candidate_id: uuid.UUID, content_hash: str) -> Resume | None:
        model = self._session.scalars(
            select(ResumeModel).where(
                ResumeModel.candidate_id == candidate_id,
                ResumeModel.content_hash == content_hash,
            )
        ).first()
        return _resume_to_entity(model) if model else None

    def get_latest_version(self, candidate_id: uuid.UUID) -> int:
        model = self._session.scalars(
            select(ResumeModel)
            .where(ResumeModel.candidate_id == candidate_id)
            .order_by(ResumeModel.version.desc())
        ).first()
        return model.version if model else 0

    def update(self, resume: Resume) -> Resume:
        model = self._session.get(ResumeModel, resume.id)
        if model is None:
            raise ValueError(f"Resume {resume.id} not found")
        model.status = resume.status.value
        model.error_message = resume.error_message
        model.parsed_at = resume.parsed_at
        self._session.flush()
        return _resume_to_entity(model)


def _job_to_entity(model: JobModel) -> Job:
    return Job(
        id=model.id,
        company_id=model.company_id,
        created_by_user_id=model.created_by_user_id,
        title=model.title,
        raw_description=model.raw_description,
        summary=model.summary,
        required_skills=model.required_skills,
        nice_to_have_skills=model.nice_to_have_skills,
        responsibilities=model.responsibilities,
        qualifications=model.qualifications,
        min_experience_years=model.min_experience_years,
        employment_type=model.employment_type,
        work_mode=JobWorkMode(model.work_mode) if model.work_mode else None,
        location=JobLocation(
            country=model.location_country,
            region=model.location_region,
            city=model.location_city,
        ),
        salary_min=model.salary_min,
        salary_max=model.salary_max,
        lifecycle_status=JobLifecycleStatus(model.lifecycle_status),
        processing_status=JobProcessingStatus(model.processing_status),
        parser_version=model.parser_version,
        content_hash=model.content_hash,
        error_message=model.error_message,
        version=model.version,
        published_at=model.published_at,
        closed_at=model.closed_at,
        parsed_at=model.parsed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        model = self._session.get(JobModel, job_id)
        return _job_to_entity(model) if model else None

    def list_by_company(self, company_id: uuid.UUID) -> list[Job]:
        models = self._session.scalars(
            select(JobModel)
            .where(JobModel.company_id == company_id)
            .order_by(JobModel.created_at.desc())
        ).all()
        return [_job_to_entity(model) for model in models]

    def add(self, job: Job) -> Job:
        model = JobModel(
            id=job.id,
            company_id=job.company_id,
            created_by_user_id=job.created_by_user_id,
            title=job.title,
            raw_description=job.raw_description,
            summary=job.summary,
            required_skills=job.required_skills,
            nice_to_have_skills=job.nice_to_have_skills,
            responsibilities=job.responsibilities,
            qualifications=job.qualifications,
            min_experience_years=job.min_experience_years,
            employment_type=job.employment_type,
            work_mode=job.work_mode.value if job.work_mode else None,
            location_country=job.location.country,
            location_region=job.location.region,
            location_city=job.location.city,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            lifecycle_status=job.lifecycle_status.value,
            processing_status=job.processing_status.value,
            parser_version=job.parser_version,
            content_hash=job.content_hash,
            error_message=job.error_message,
            version=job.version,
            published_at=job.published_at,
            closed_at=job.closed_at,
            parsed_at=job.parsed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self._session.add(model)
        self._session.flush()
        return _job_to_entity(model)

    def update(self, job: Job) -> Job:
        model = self._session.get(JobModel, job.id)
        if model is None:
            raise ValueError(f"Job {job.id} not found")
        model.title = job.title
        model.raw_description = job.raw_description
        model.summary = job.summary
        model.required_skills = job.required_skills
        model.nice_to_have_skills = job.nice_to_have_skills
        model.responsibilities = job.responsibilities
        model.qualifications = job.qualifications
        model.min_experience_years = job.min_experience_years
        model.employment_type = job.employment_type
        model.work_mode = job.work_mode.value if job.work_mode else None
        model.location_country = job.location.country
        model.location_region = job.location.region
        model.location_city = job.location.city
        model.salary_min = job.salary_min
        model.salary_max = job.salary_max
        model.lifecycle_status = job.lifecycle_status.value
        model.processing_status = job.processing_status.value
        model.parser_version = job.parser_version
        model.content_hash = job.content_hash
        model.error_message = job.error_message
        model.version = job.version
        model.published_at = job.published_at
        model.closed_at = job.closed_at
        model.parsed_at = job.parsed_at
        model.updated_at = job.updated_at
        self._session.flush()
        return _job_to_entity(model)

    def delete(self, job_id: uuid.UUID) -> None:
        model = self._session.get(JobModel, job_id)
        if model is not None:
            self._session.delete(model)
            self._session.flush()


def _job_version_to_entity(model: JobVersionModel) -> JobVersion:
    return JobVersion(
        id=model.id,
        job_id=model.job_id,
        version=model.version,
        raw_description=model.raw_description,
        content_hash=model.content_hash,
        parser_version=model.parser_version,
        extracted_snapshot=model.extracted_snapshot,
        created_at=model.created_at,
    )


class SqlAlchemyJobVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, version: JobVersion) -> JobVersion:
        model = JobVersionModel(
            id=version.id,
            job_id=version.job_id,
            version=version.version,
            raw_description=version.raw_description,
            content_hash=version.content_hash,
            parser_version=version.parser_version,
            extracted_snapshot=version.extracted_snapshot,
            created_at=version.created_at,
        )
        self._session.add(model)
        self._session.flush()
        return _job_version_to_entity(model)

    def list_by_job(self, job_id: uuid.UUID) -> list[JobVersion]:
        models = self._session.scalars(
            select(JobVersionModel)
            .where(JobVersionModel.job_id == job_id)
            .order_by(JobVersionModel.version.desc())
        ).all()
        return [_job_version_to_entity(model) for model in models]


def _match_score_to_entity(model: MatchScoreModel) -> MatchScore:
    return MatchScore(
        id=model.id,
        candidate_id=model.candidate_id,
        job_id=model.job_id,
        overall_score=model.overall_score,
        semantic_score=model.semantic_score,
        skill_overlap_score=model.skill_overlap_score,
        experience_fit_score=model.experience_fit_score,
        salary_fit_score=model.salary_fit_score,
        location_fit_score=model.location_fit_score,
        rerank_score=model.rerank_score,
        matcher_version=model.matcher_version,
        candidate_content_hash=model.candidate_content_hash,
        job_content_hash=model.job_content_hash,
        computed_at=model.computed_at,
    )


class SqlAlchemyMatchScoreRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, match_score: MatchScore) -> MatchScore:
        model = MatchScoreModel(
            id=match_score.id,
            candidate_id=match_score.candidate_id,
            job_id=match_score.job_id,
            overall_score=match_score.overall_score,
            semantic_score=match_score.semantic_score,
            skill_overlap_score=match_score.skill_overlap_score,
            experience_fit_score=match_score.experience_fit_score,
            salary_fit_score=match_score.salary_fit_score,
            location_fit_score=match_score.location_fit_score,
            rerank_score=match_score.rerank_score,
            matcher_version=match_score.matcher_version,
            candidate_content_hash=match_score.candidate_content_hash,
            job_content_hash=match_score.job_content_hash,
            computed_at=match_score.computed_at,
        )
        self._session.add(model)
        self._session.flush()
        return _match_score_to_entity(model)

    def get_latest_for_pair(
        self, candidate_id: uuid.UUID, job_id: uuid.UUID, matcher_version: str
    ) -> MatchScore | None:
        model = self._session.scalars(
            select(MatchScoreModel)
            .where(
                MatchScoreModel.candidate_id == candidate_id,
                MatchScoreModel.job_id == job_id,
                MatchScoreModel.matcher_version == matcher_version,
            )
            .order_by(MatchScoreModel.computed_at.desc())
            .limit(1)
        ).first()
        return _match_score_to_entity(model) if model else None

    def list_latest_for_job(self, job_id: uuid.UUID) -> list[MatchScore]:
        models = self._session.scalars(
            select(MatchScoreModel)
            .distinct(MatchScoreModel.candidate_id)
            .where(MatchScoreModel.job_id == job_id)
            .order_by(MatchScoreModel.candidate_id, MatchScoreModel.computed_at.desc())
        ).all()
        return [_match_score_to_entity(model) for model in models]

    def list_latest_for_candidate(self, candidate_id: uuid.UUID) -> list[MatchScore]:
        models = self._session.scalars(
            select(MatchScoreModel)
            .distinct(MatchScoreModel.job_id)
            .where(MatchScoreModel.candidate_id == candidate_id)
            .order_by(MatchScoreModel.job_id, MatchScoreModel.computed_at.desc())
        ).all()
        return [_match_score_to_entity(model) for model in models]


def _application_to_entity(model: ApplicationModel) -> Application:
    return Application(
        id=model.id,
        job_id=model.job_id,
        candidate_id=model.candidate_id,
        status=ApplicationStatus(model.status),
        invited_by_user_id=model.invited_by_user_id,
        applied_at=model.applied_at,
        status_updated_at=model.status_updated_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyApplicationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, application_id: uuid.UUID) -> Application | None:
        model = self._session.get(ApplicationModel, application_id)
        return _application_to_entity(model) if model else None

    def get_by_job_and_candidate(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Application | None:
        model = self._session.scalars(
            select(ApplicationModel).where(
                ApplicationModel.job_id == job_id,
                ApplicationModel.candidate_id == candidate_id,
            )
        ).first()
        return _application_to_entity(model) if model else None

    def list_by_job(self, job_id: uuid.UUID) -> list[Application]:
        models = self._session.scalars(
            select(ApplicationModel).where(ApplicationModel.job_id == job_id)
        ).all()
        return [_application_to_entity(model) for model in models]

    def list_by_candidate(self, candidate_id: uuid.UUID) -> list[Application]:
        models = self._session.scalars(
            select(ApplicationModel).where(ApplicationModel.candidate_id == candidate_id)
        ).all()
        return [_application_to_entity(model) for model in models]

    def add(self, application: Application) -> Application:
        model = ApplicationModel(
            id=application.id,
            job_id=application.job_id,
            candidate_id=application.candidate_id,
            status=application.status.value,
            invited_by_user_id=application.invited_by_user_id,
            applied_at=application.applied_at,
            status_updated_at=application.status_updated_at,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
        self._session.add(model)
        self._session.flush()
        return _application_to_entity(model)

    def update(self, application: Application) -> Application:
        model = self._session.get(ApplicationModel, application.id)
        if model is None:
            raise ValueError(f"Application {application.id} not found")
        model.status = application.status.value
        model.invited_by_user_id = application.invited_by_user_id
        model.applied_at = application.applied_at
        model.status_updated_at = application.status_updated_at
        model.updated_at = application.updated_at
        self._session.flush()
        return _application_to_entity(model)
