import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session
from src.domain.candidate.entities import (
    Candidate,
    Education,
    Location,
    Resume,
    ResumeStatus,
    WorkExperience,
    WorkMode,
)
from src.domain.company.entities import Company, CompanyMember, CompanyMemberRole
from src.domain.job.entities import Job, JobLifecycleStatus, JobProcessingStatus, JobVersion
from src.domain.job.entities import Location as JobLocation
from src.domain.job.entities import WorkMode as JobWorkMode
from src.domain.matching.entities import MatchScore
from src.domain.user.entities import User, UserRole
from src.infrastructure.db.repositories import (
    SqlAlchemyCandidateRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyJobVersionRepository,
    SqlAlchemyMatchScoreRepository,
    SqlAlchemyResumeRepository,
    SqlAlchemyUserRepository,
)


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
                match_threshold=70,
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
                match_threshold=70,
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
                match_threshold=70,
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


class TestSqlAlchemyCandidateRepository:
    def test_add_and_get_by_user_id_round_trips(self, db_session: Session) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        candidate_repo = SqlAlchemyCandidateRepository(db_session)
        user = user_repo.add(_make_user(email="candidate@example.com"))

        now = datetime.now(UTC)
        candidate = candidate_repo.add(
            Candidate(
                id=uuid.uuid4(),
                user_id=user.id,
                full_name="Jane Doe",
                headline="Senior Engineer",
                summary="Experienced.",
                skills=["Python", "SQL"],
                total_experience_years=7.5,
                location=Location(country="US", region="CA", city="SF"),
                desired_salary_min=150000,
                desired_salary_max=200000,
                work_mode_preference=WorkMode.REMOTE,
                work_experience=[
                    WorkExperience(
                        company="Acme",
                        title="Engineer",
                        start_date=date(2020, 1, 1),
                        end_date=None,
                        description="Built things.",
                    )
                ],
                education=[
                    Education(
                        institution="State University",
                        degree="BS",
                        field_of_study="CS",
                        start_date=date(2012, 1, 1),
                        end_date=date(2016, 1, 1),
                    )
                ],
                created_at=now,
                updated_at=now,
            )
        )

        fetched = candidate_repo.get_by_user_id(user.id)

        assert fetched is not None
        assert fetched.id == candidate.id
        assert fetched.skills == ["Python", "SQL"]
        assert fetched.location.city == "SF"
        assert fetched.work_mode_preference == WorkMode.REMOTE
        assert fetched.work_experience[0].company == "Acme"
        assert fetched.work_experience[0].start_date == date(2020, 1, 1)
        assert fetched.education[0].institution == "State University"

    def test_update_persists_changes(self, db_session: Session) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        candidate_repo = SqlAlchemyCandidateRepository(db_session)
        user = user_repo.add(_make_user(email="candidate2@example.com"))
        now = datetime.now(UTC)
        candidate = candidate_repo.add(
            Candidate(
                id=uuid.uuid4(),
                user_id=user.id,
                full_name=None,
                headline=None,
                summary=None,
                skills=[],
                total_experience_years=None,
                location=Location(),
                desired_salary_min=None,
                desired_salary_max=None,
                work_mode_preference=None,
                created_at=now,
                updated_at=now,
            )
        )

        candidate.full_name = "Updated Name"
        candidate.skills = ["Go"]
        candidate_repo.update(candidate)

        fetched = candidate_repo.get_by_id(candidate.id)
        assert fetched is not None
        assert fetched.full_name == "Updated Name"
        assert fetched.skills == ["Go"]


class TestSqlAlchemyResumeRepository:
    def _make_candidate(self, db_session: Session, email: str) -> Candidate:
        user_repo = SqlAlchemyUserRepository(db_session)
        candidate_repo = SqlAlchemyCandidateRepository(db_session)
        user = user_repo.add(_make_user(email=email))
        now = datetime.now(UTC)
        return candidate_repo.add(
            Candidate(
                id=uuid.uuid4(),
                user_id=user.id,
                full_name=None,
                headline=None,
                summary=None,
                skills=[],
                total_experience_years=None,
                location=Location(),
                desired_salary_min=None,
                desired_salary_max=None,
                work_mode_preference=None,
                created_at=now,
                updated_at=now,
            )
        )

    def test_add_and_dedupe_by_content_hash(self, db_session: Session) -> None:
        candidate = self._make_candidate(db_session, "resume-owner@example.com")
        resume_repo = SqlAlchemyResumeRepository(db_session)
        now = datetime.now(UTC)

        resume = resume_repo.add(
            Resume(
                id=uuid.uuid4(),
                candidate_id=candidate.id,
                version=1,
                s3_key=f"resumes/{candidate.id}/1.pdf",
                original_filename="resume.pdf",
                file_type="pdf",
                content_type="application/pdf",
                file_size=123,
                content_hash="abc123",
                status=ResumeStatus.PENDING,
                parser_version="v1",
                error_message=None,
                uploaded_at=now,
                parsed_at=None,
            )
        )

        found = resume_repo.get_by_content_hash(candidate.id, "abc123")
        assert found is not None
        assert found.id == resume.id
        assert resume_repo.get_latest_version(candidate.id) == 1

    def test_update_status_persists(self, db_session: Session) -> None:
        candidate = self._make_candidate(db_session, "resume-owner2@example.com")
        resume_repo = SqlAlchemyResumeRepository(db_session)
        now = datetime.now(UTC)
        resume = resume_repo.add(
            Resume(
                id=uuid.uuid4(),
                candidate_id=candidate.id,
                version=1,
                s3_key=f"resumes/{candidate.id}/1.pdf",
                original_filename="resume.pdf",
                file_type="pdf",
                content_type="application/pdf",
                file_size=123,
                content_hash="def456",
                status=ResumeStatus.PENDING,
                parser_version="v1",
                error_message=None,
                uploaded_at=now,
                parsed_at=None,
            )
        )

        resume.status = ResumeStatus.READY
        resume.parsed_at = now
        resume_repo.update(resume)

        fetched = resume_repo.get_by_id(resume.id)
        assert fetched is not None
        assert fetched.status == ResumeStatus.READY

    def test_list_by_candidate_scopes_correctly(self, db_session: Session) -> None:
        candidate_a = self._make_candidate(db_session, "a-owner@example.com")
        candidate_b = self._make_candidate(db_session, "b-owner@example.com")
        resume_repo = SqlAlchemyResumeRepository(db_session)
        now = datetime.now(UTC)

        resume_repo.add(
            Resume(
                id=uuid.uuid4(),
                candidate_id=candidate_a.id,
                version=1,
                s3_key="a.pdf",
                original_filename="a.pdf",
                file_type="pdf",
                content_type="application/pdf",
                file_size=1,
                content_hash="hash-a",
                status=ResumeStatus.PENDING,
                parser_version="v1",
                error_message=None,
                uploaded_at=now,
                parsed_at=None,
            )
        )
        resume_repo.add(
            Resume(
                id=uuid.uuid4(),
                candidate_id=candidate_b.id,
                version=1,
                s3_key="b.pdf",
                original_filename="b.pdf",
                file_type="pdf",
                content_type="application/pdf",
                file_size=1,
                content_hash="hash-b",
                status=ResumeStatus.PENDING,
                parser_version="v1",
                error_message=None,
                uploaded_at=now,
                parsed_at=None,
            )
        )

        resumes_a = resume_repo.list_by_candidate(candidate_a.id)

        assert len(resumes_a) == 1
        assert resumes_a[0].s3_key == "a.pdf"


def _make_job(company_id: uuid.UUID, user_id: uuid.UUID, **overrides: object) -> Job:
    now = datetime.now(UTC)
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        company_id=company_id,
        created_by_user_id=user_id,
        title="Backend Engineer",
        raw_description="We are hiring a backend engineer.",
        summary=None,
        required_skills=[],
        nice_to_have_skills=[],
        responsibilities=[],
        qualifications=[],
        min_experience_years=None,
        employment_type=None,
        work_mode=None,
        location=JobLocation(),
        salary_min=None,
        salary_max=None,
        lifecycle_status=JobLifecycleStatus.DRAFT,
        processing_status=JobProcessingStatus.PENDING,
        parser_version="v1",
        content_hash="deadbeef",
        error_message=None,
        version=1,
        published_at=None,
        closed_at=None,
        parsed_at=None,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return Job(**defaults)  # type: ignore[arg-type]


class TestSqlAlchemyJobRepository:
    def _make_company_and_user(self, db_session: Session, email: str) -> tuple[Company, User]:
        user_repo = SqlAlchemyUserRepository(db_session)
        company_repo = SqlAlchemyCompanyRepository(db_session)
        user = user_repo.add(_make_user(email=email))
        now = datetime.now(UTC)
        company = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="Acme Jobs Inc",
                slug=f"acme-jobs-{uuid.uuid4().hex[:8]}",
                plan="free",
                usage_counters={},
                match_threshold=70,
                created_at=now,
                updated_at=now,
            )
        )
        return company, user

    def test_add_and_get_by_id_round_trips(self, db_session: Session) -> None:
        company, user = self._make_company_and_user(db_session, "job-owner@example.com")
        job_repo = SqlAlchemyJobRepository(db_session)

        job = job_repo.add(
            _make_job(
                company.id,
                user.id,
                required_skills=["Python", "SQL"],
                work_mode=JobWorkMode.REMOTE,
                location=JobLocation(country="US", region="CA", city="SF"),
                salary_min=120000,
                salary_max=160000,
            )
        )

        fetched = job_repo.get_by_id(job.id)
        assert fetched is not None
        assert fetched.title == "Backend Engineer"
        assert fetched.required_skills == ["Python", "SQL"]
        assert fetched.work_mode == JobWorkMode.REMOTE
        assert fetched.location.city == "SF"

    def test_list_by_company_scopes_correctly(self, db_session: Session) -> None:
        company_a, user_a = self._make_company_and_user(db_session, "job-a@example.com")
        company_b, user_b = self._make_company_and_user(db_session, "job-b@example.com")
        job_repo = SqlAlchemyJobRepository(db_session)
        job_repo.add(_make_job(company_a.id, user_a.id, title="Job A"))
        job_repo.add(_make_job(company_b.id, user_b.id, title="Job B"))

        jobs_a = job_repo.list_by_company(company_a.id)

        assert len(jobs_a) == 1
        assert jobs_a[0].title == "Job A"

    def test_update_persists_changes(self, db_session: Session) -> None:
        company, user = self._make_company_and_user(db_session, "job-update@example.com")
        job_repo = SqlAlchemyJobRepository(db_session)
        job = job_repo.add(_make_job(company.id, user.id))

        job.lifecycle_status = JobLifecycleStatus.PUBLISHED
        job.processing_status = JobProcessingStatus.READY
        job_repo.update(job)

        fetched = job_repo.get_by_id(job.id)
        assert fetched is not None
        assert fetched.lifecycle_status == JobLifecycleStatus.PUBLISHED
        assert fetched.processing_status == JobProcessingStatus.READY

    def test_delete_removes_job(self, db_session: Session) -> None:
        company, user = self._make_company_and_user(db_session, "job-delete@example.com")
        job_repo = SqlAlchemyJobRepository(db_session)
        job = job_repo.add(_make_job(company.id, user.id))

        job_repo.delete(job.id)

        assert job_repo.get_by_id(job.id) is None


class TestSqlAlchemyJobVersionRepository:
    def test_add_and_list_by_job(self, db_session: Session) -> None:
        user_repo = SqlAlchemyUserRepository(db_session)
        company_repo = SqlAlchemyCompanyRepository(db_session)
        job_repo = SqlAlchemyJobRepository(db_session)
        job_version_repo = SqlAlchemyJobVersionRepository(db_session)

        user = user_repo.add(_make_user(email="job-version@example.com"))
        now = datetime.now(UTC)
        company = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="Versioned Co",
                slug=f"versioned-co-{uuid.uuid4().hex[:8]}",
                plan="free",
                usage_counters={},
                match_threshold=70,
                created_at=now,
                updated_at=now,
            )
        )
        job = job_repo.add(_make_job(company.id, user.id))

        job_version_repo.add(
            JobVersion(
                id=uuid.uuid4(),
                job_id=job.id,
                version=1,
                raw_description=job.raw_description,
                content_hash=job.content_hash,
                parser_version="v1",
                extracted_snapshot={"required_skills": ["Python"]},
                created_at=now,
            )
        )

        versions = job_version_repo.list_by_job(job.id)
        assert len(versions) == 1
        assert versions[0].extracted_snapshot["required_skills"] == ["Python"]


class TestCompanyMatchThreshold:
    def test_match_threshold_round_trips_and_updates(self, db_session: Session) -> None:
        company_repo = SqlAlchemyCompanyRepository(db_session)
        now = datetime.now(UTC)
        company = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="Threshold Co",
                slug=f"threshold-co-{uuid.uuid4().hex[:8]}",
                plan="free",
                usage_counters={},
                match_threshold=70,
                created_at=now,
                updated_at=now,
            )
        )
        assert company.match_threshold == 70

        company.match_threshold = 85
        updated = company_repo.update(company)
        assert updated.match_threshold == 85

        fetched = company_repo.get_by_id(company.id)
        assert fetched is not None
        assert fetched.match_threshold == 85


def _make_match_score(
    candidate_id: uuid.UUID, job_id: uuid.UUID, **overrides: object
) -> MatchScore:
    defaults: dict[str, object] = dict(
        id=uuid.uuid4(),
        candidate_id=candidate_id,
        job_id=job_id,
        overall_score=75.0,
        semantic_score=80.0,
        skill_overlap_score=70.0,
        experience_fit_score=100.0,
        salary_fit_score=100.0,
        location_fit_score=100.0,
        rerank_score=60.0,
        matcher_version="v1",
        candidate_content_hash="cand-hash",
        job_content_hash="job-hash",
        computed_at=datetime.now(UTC),
    )
    defaults.update(overrides)
    return MatchScore(**defaults)  # type: ignore[arg-type]


class TestSqlAlchemyMatchScoreRepository:
    def _make_candidate_and_job(
        self, db_session: Session, email: str
    ) -> tuple[uuid.UUID, uuid.UUID]:
        user_repo = SqlAlchemyUserRepository(db_session)
        candidate_repo = SqlAlchemyCandidateRepository(db_session)
        company_repo = SqlAlchemyCompanyRepository(db_session)
        job_repo = SqlAlchemyJobRepository(db_session)

        user = user_repo.add(_make_user(email=email))
        now = datetime.now(UTC)
        candidate = candidate_repo.add(
            Candidate(
                id=uuid.uuid4(),
                user_id=user.id,
                full_name=None,
                headline=None,
                summary=None,
                skills=[],
                total_experience_years=None,
                location=Location(),
                desired_salary_min=None,
                desired_salary_max=None,
                work_mode_preference=None,
                created_at=now,
                updated_at=now,
            )
        )
        company = company_repo.add(
            Company(
                id=uuid.uuid4(),
                name="Match Co",
                slug=f"match-co-{uuid.uuid4().hex[:8]}",
                plan="free",
                usage_counters={},
                match_threshold=70,
                created_at=now,
                updated_at=now,
            )
        )
        job = job_repo.add(_make_job(company.id, user.id))
        return candidate.id, job.id

    def test_add_and_get_latest_for_pair(self, db_session: Session) -> None:
        match_score_repo = SqlAlchemyMatchScoreRepository(db_session)
        candidate_id, job_id = self._make_candidate_and_job(db_session, "match-pair@example.com")

        match_score_repo.add(_make_match_score(candidate_id, job_id))

        found = match_score_repo.get_latest_for_pair(candidate_id, job_id, "v1")
        assert found is not None
        assert found.candidate_content_hash == "cand-hash"

        assert match_score_repo.get_latest_for_pair(candidate_id, job_id, "v2") is None

    def test_list_latest_for_job_returns_one_row_per_candidate(self, db_session: Session) -> None:
        match_score_repo = SqlAlchemyMatchScoreRepository(db_session)
        candidate_id, job_id = self._make_candidate_and_job(db_session, "match-job-a@example.com")

        older = datetime.now(UTC)
        match_score_repo.add(
            _make_match_score(candidate_id, job_id, overall_score=50.0, computed_at=older)
        )
        newer = datetime.now(UTC)
        match_score_repo.add(
            _make_match_score(candidate_id, job_id, overall_score=90.0, computed_at=newer)
        )

        results = match_score_repo.list_latest_for_job(job_id)

        assert len(results) == 1
        assert results[0].overall_score == 90.0

    def test_list_latest_for_candidate_returns_one_row_per_job(self, db_session: Session) -> None:
        match_score_repo = SqlAlchemyMatchScoreRepository(db_session)
        candidate_id, job_id = self._make_candidate_and_job(
            db_session, "match-candidate-a@example.com"
        )

        match_score_repo.add(_make_match_score(candidate_id, job_id))

        results = match_score_repo.list_latest_for_candidate(candidate_id)

        assert len(results) == 1
        assert results[0].job_id == job_id
