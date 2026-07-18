import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.application.auth.ports import AccessTokenClaims, GoogleOAuthClient, GoogleUserInfo
from src.application.auth.service import AuthService
from src.application.candidate.parsing_service import ResumeParsingService
from src.application.candidate.service import CandidateService
from src.application.company.service import CompanyService
from src.application.job.parsing_service import JobParsingService
from src.application.job.service import JobService
from src.domain.candidate.entities import Candidate, Resume
from src.domain.company.entities import Company, CompanyInvite, CompanyMember
from src.domain.job.entities import Job, JobVersion
from src.domain.user.entities import EmailVerificationToken, PasswordResetToken, RefreshToken, User


class FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, User] = {}

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self._by_id.get(user_id)

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    def get_by_google_sub(self, sub: str) -> User | None:
        return next((u for u in self._by_id.values() if u.oauth_google_sub == sub), None)

    def add(self, user: User) -> User:
        self._by_id[user.id] = user
        return user

    def update(self, user: User) -> User:
        self._by_id[user.id] = user
        return user


class FakeRefreshTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, RefreshToken] = {}

    def add(self, token: RefreshToken) -> RefreshToken:
        self._by_id[token.id] = token
        return token

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return next((t for t in self._by_id.values() if t.token_hash == token_hash), None)

    def revoke(self, token_id: uuid.UUID, replaced_by_id: uuid.UUID | None = None) -> None:
        token = self._by_id.get(token_id)
        if token is not None:
            token.revoked_at = datetime.now(UTC)
            if replaced_by_id is not None:
                token.replaced_by_id = replaced_by_id

    def revoke_family(self, family_id: uuid.UUID) -> None:
        for token in self._by_id.values():
            if token.family_id == family_id and token.revoked_at is None:
                token.revoked_at = datetime.now(UTC)

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        for token in self._by_id.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = datetime.now(UTC)


class FakeEmailVerificationTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, EmailVerificationToken] = {}

    def add(self, token: EmailVerificationToken) -> EmailVerificationToken:
        self._by_id[token.id] = token
        return token

    def get_by_hash(self, token_hash: str) -> EmailVerificationToken | None:
        return next((t for t in self._by_id.values() if t.token_hash == token_hash), None)

    def mark_used(self, token_id: uuid.UUID) -> None:
        token = self._by_id.get(token_id)
        if token is not None:
            token.used_at = datetime.now(UTC)


class FakePasswordResetTokenRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, PasswordResetToken] = {}

    def add(self, token: PasswordResetToken) -> PasswordResetToken:
        self._by_id[token.id] = token
        return token

    def get_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        return next((t for t in self._by_id.values() if t.token_hash == token_hash), None)

    def mark_used(self, token_id: uuid.UUID) -> None:
        token = self._by_id.get(token_id)
        if token is not None:
            token.used_at = datetime.now(UTC)


class FakeCompanyRepository:
    def __init__(self) -> None:
        self._companies: dict[uuid.UUID, Company] = {}
        self._members: dict[uuid.UUID, CompanyMember] = {}
        self._invites: dict[uuid.UUID, CompanyInvite] = {}

    def get_by_id(self, company_id: uuid.UUID) -> Company | None:
        return self._companies.get(company_id)

    def get_by_slug(self, slug: str) -> Company | None:
        return next((c for c in self._companies.values() if c.slug == slug), None)

    def add(self, company: Company) -> Company:
        self._companies[company.id] = company
        return company

    def update(self, company: Company) -> Company:
        self._companies[company.id] = company
        return company

    def add_member(self, member: CompanyMember) -> CompanyMember:
        self._members[member.id] = member
        return member

    def get_member(self, company_id: uuid.UUID, user_id: uuid.UUID) -> CompanyMember | None:
        return next(
            (
                m
                for m in self._members.values()
                if m.company_id == company_id and m.user_id == user_id
            ),
            None,
        )

    def list_members(self, company_id: uuid.UUID) -> list[CompanyMember]:
        return [m for m in self._members.values() if m.company_id == company_id]

    def add_invite(self, invite: CompanyInvite) -> CompanyInvite:
        self._invites[invite.id] = invite
        return invite

    def get_invite_by_hash(self, token_hash: str) -> CompanyInvite | None:
        return next((i for i in self._invites.values() if i.token_hash == token_hash), None)

    def mark_invite_accepted(self, invite_id: uuid.UUID) -> None:
        invite = self._invites.get(invite_id)
        if invite is not None:
            invite.accepted_at = datetime.now(UTC)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeAccessTokenService:
    def create(self, user: User) -> str:
        return f"access:{user.id}:{user.role.value}"

    def decode(self, token: str) -> AccessTokenClaims:
        try:
            _, raw_id, role = token.split(":")
            return AccessTokenClaims(user_id=uuid.UUID(raw_id), role=role)
        except ValueError as exc:
            raise ValueError("Invalid access token") from exc


@dataclass
class FakeEmailSender:
    sent: list[tuple[str, str, str]] = field(default_factory=list)

    def send_verification_email(self, user: User, raw_token: str) -> None:
        self.sent.append(("verification", user.email, raw_token))

    def send_password_reset_email(self, user: User, raw_token: str) -> None:
        self.sent.append(("password_reset", user.email, raw_token))

    def send_invite_email(self, invite: CompanyInvite, company_name: str, raw_token: str) -> None:
        self.sent.append(("invite", invite.email, raw_token))


@dataclass
class FakeGoogleOAuthClient:
    user_info: GoogleUserInfo | None = None
    error: str | None = None

    def exchange_code(self, code: str) -> GoogleUserInfo:
        if self.error is not None:
            raise ValueError(self.error)
        assert self.user_info is not None
        return self.user_info


@dataclass
class AuthServiceHarness:
    service: AuthService
    users: FakeUserRepository
    refresh_tokens: FakeRefreshTokenRepository
    companies: FakeCompanyRepository
    email_sender: FakeEmailSender


def build_auth_service(
    google_oauth_client: GoogleOAuthClient | None = None,
    refresh_token_expire_days: int = 30,
) -> AuthServiceHarness:
    users = FakeUserRepository()
    refresh_tokens = FakeRefreshTokenRepository()
    companies = FakeCompanyRepository()
    email_sender = FakeEmailSender()

    service = AuthService(
        user_repo=users,
        refresh_token_repo=refresh_tokens,
        email_verification_repo=FakeEmailVerificationTokenRepository(),
        password_reset_repo=FakePasswordResetTokenRepository(),
        company_repo=companies,
        password_hasher=FakePasswordHasher(),
        access_token_service=FakeAccessTokenService(),
        email_sender=email_sender,
        refresh_token_expire_days=refresh_token_expire_days,
        google_oauth_client=google_oauth_client,
    )
    return AuthServiceHarness(
        service=service,
        users=users,
        refresh_tokens=refresh_tokens,
        companies=companies,
        email_sender=email_sender,
    )


@dataclass
class CompanyServiceHarness:
    service: CompanyService
    companies: FakeCompanyRepository
    email_sender: FakeEmailSender


def build_company_service() -> CompanyServiceHarness:
    companies = FakeCompanyRepository()
    email_sender = FakeEmailSender()
    service = CompanyService(companies, email_sender)
    return CompanyServiceHarness(service=service, companies=companies, email_sender=email_sender)


class FakeCandidateRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, Candidate] = {}

    def get_by_id(self, candidate_id: uuid.UUID) -> Candidate | None:
        return self._by_id.get(candidate_id)

    def get_by_user_id(self, user_id: uuid.UUID) -> Candidate | None:
        return next((c for c in self._by_id.values() if c.user_id == user_id), None)

    def add(self, candidate: Candidate) -> Candidate:
        self._by_id[candidate.id] = candidate
        return candidate

    def update(self, candidate: Candidate) -> Candidate:
        self._by_id[candidate.id] = candidate
        return candidate


class FakeResumeRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, Resume] = {}

    def add(self, resume: Resume) -> Resume:
        self._by_id[resume.id] = resume
        return resume

    def get_by_id(self, resume_id: uuid.UUID) -> Resume | None:
        return self._by_id.get(resume_id)

    def list_by_candidate(self, candidate_id: uuid.UUID) -> list[Resume]:
        return [r for r in self._by_id.values() if r.candidate_id == candidate_id]

    def get_by_content_hash(self, candidate_id: uuid.UUID, content_hash: str) -> Resume | None:
        return next(
            (
                r
                for r in self._by_id.values()
                if r.candidate_id == candidate_id and r.content_hash == content_hash
            ),
            None,
        )

    def get_latest_version(self, candidate_id: uuid.UUID) -> int:
        versions = [r.version for r in self._by_id.values() if r.candidate_id == candidate_id]
        return max(versions, default=0)

    def update(self, resume: Resume) -> Resume:
        self._by_id[resume.id] = resume
        return resume


@dataclass
class FakeStorageClient:
    files: dict[str, bytes] = field(default_factory=dict)
    bucket_ensured: bool = False

    def ensure_bucket(self) -> None:
        self.bucket_ensured = True

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = data

    def download(self, key: str) -> bytes:
        return self.files[key]

    def generate_presigned_url(self, key: str, expires_in_seconds: int) -> str:
        return f"https://fake-storage.test/{key}?expires_in={expires_in_seconds}"


@dataclass
class FakeResumeProcessingDispatcher:
    dispatched: list[uuid.UUID] = field(default_factory=list)

    def dispatch_parse(self, resume_id: uuid.UUID) -> None:
        self.dispatched.append(resume_id)


@dataclass
class FakeTextExtractor:
    text: str = "Jane Doe\nSenior Engineer\nPython, SQL, Leadership"

    def extract_text(self, file_bytes: bytes, file_type: str) -> str:
        return self.text


@dataclass
class FakeLLMClient:
    result: object = None
    error: Exception | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def extract_structured(self, instructions: str, data: str, schema: type) -> object:  # type: ignore[type-arg]
        self.calls.append((instructions, data))
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@dataclass
class FakeEmbeddingClient:
    vector: list[float] = field(default_factory=lambda: [0.1] * 1024)
    calls: list[list[str]] = field(default_factory=list)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [self.vector for _ in texts]


@dataclass
class FakeVectorStore:
    collections: dict[str, int] = field(default_factory=dict)
    points: dict[str, dict[str, tuple[list[float], dict[str, object]]]] = field(
        default_factory=dict
    )

    def ensure_collection(self, collection: str, vector_size: int) -> None:
        self.collections[collection] = vector_size

    def upsert(
        self, collection: str, point_id: str, vector: list[float], payload: dict[str, object]
    ) -> None:
        self.points.setdefault(collection, {})[point_id] = (vector, payload)

    def delete(self, collection: str, point_id: str) -> None:
        self.points.get(collection, {}).pop(point_id, None)


@dataclass
class CandidateServiceHarness:
    service: CandidateService
    candidates: FakeCandidateRepository
    resumes: FakeResumeRepository
    storage: FakeStorageClient
    dispatcher: FakeResumeProcessingDispatcher


def build_candidate_service() -> CandidateServiceHarness:
    candidates = FakeCandidateRepository()
    resumes = FakeResumeRepository()
    storage = FakeStorageClient()
    dispatcher = FakeResumeProcessingDispatcher()
    service = CandidateService(candidates, resumes, storage, dispatcher)
    return CandidateServiceHarness(
        service=service,
        candidates=candidates,
        resumes=resumes,
        storage=storage,
        dispatcher=dispatcher,
    )


@dataclass
class ParsingServiceHarness:
    service: ResumeParsingService
    candidates: FakeCandidateRepository
    resumes: FakeResumeRepository
    storage: FakeStorageClient
    text_extractor: FakeTextExtractor
    llm: FakeLLMClient
    embeddings: FakeEmbeddingClient
    vector_store: FakeVectorStore


def build_parsing_service(
    llm_result: object = None,
    llm_error: Exception | None = None,
) -> ParsingServiceHarness:
    candidates = FakeCandidateRepository()
    resumes = FakeResumeRepository()
    storage = FakeStorageClient()
    text_extractor = FakeTextExtractor()
    llm = FakeLLMClient(result=llm_result, error=llm_error)
    embeddings = FakeEmbeddingClient()
    vector_store = FakeVectorStore()

    service = ResumeParsingService(
        candidate_repo=candidates,
        resume_repo=resumes,
        storage=storage,
        text_extractor=text_extractor,
        llm_client=llm,
        embedding_client=embeddings,
        vector_store=vector_store,
    )
    return ParsingServiceHarness(
        service=service,
        candidates=candidates,
        resumes=resumes,
        storage=storage,
        text_extractor=text_extractor,
        llm=llm,
        embeddings=embeddings,
        vector_store=vector_store,
    )


class FakeJobRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, Job] = {}

    def get_by_id(self, job_id: uuid.UUID) -> Job | None:
        return self._by_id.get(job_id)

    def list_by_company(self, company_id: uuid.UUID) -> list[Job]:
        return [j for j in self._by_id.values() if j.company_id == company_id]

    def add(self, job: Job) -> Job:
        self._by_id[job.id] = job
        return job

    def update(self, job: Job) -> Job:
        self._by_id[job.id] = job
        return job

    def delete(self, job_id: uuid.UUID) -> None:
        self._by_id.pop(job_id, None)


class FakeJobVersionRepository:
    def __init__(self) -> None:
        self._by_id: dict[uuid.UUID, JobVersion] = {}

    def add(self, version: JobVersion) -> JobVersion:
        self._by_id[version.id] = version
        return version

    def list_by_job(self, job_id: uuid.UUID) -> list[JobVersion]:
        return [v for v in self._by_id.values() if v.job_id == job_id]


@dataclass
class FakeJobProcessingDispatcher:
    dispatched: list[uuid.UUID] = field(default_factory=list)

    def dispatch_parse(self, job_id: uuid.UUID) -> None:
        self.dispatched.append(job_id)


@dataclass
class JobServiceHarness:
    service: JobService
    jobs: FakeJobRepository
    dispatcher: FakeJobProcessingDispatcher


def build_job_service() -> JobServiceHarness:
    jobs = FakeJobRepository()
    dispatcher = FakeJobProcessingDispatcher()
    service = JobService(jobs, dispatcher)
    return JobServiceHarness(service=service, jobs=jobs, dispatcher=dispatcher)


@dataclass
class JobParsingServiceHarness:
    service: JobParsingService
    jobs: FakeJobRepository
    job_versions: FakeJobVersionRepository
    llm: FakeLLMClient
    embeddings: FakeEmbeddingClient
    vector_store: FakeVectorStore


def build_job_parsing_service(
    llm_result: object = None,
    llm_error: Exception | None = None,
) -> JobParsingServiceHarness:
    jobs = FakeJobRepository()
    job_versions = FakeJobVersionRepository()
    llm = FakeLLMClient(result=llm_result, error=llm_error)
    embeddings = FakeEmbeddingClient()
    vector_store = FakeVectorStore()

    service = JobParsingService(
        job_repo=jobs,
        job_version_repo=job_versions,
        llm_client=llm,
        embedding_client=embeddings,
        vector_store=vector_store,
    )
    return JobParsingServiceHarness(
        service=service,
        jobs=jobs,
        job_versions=job_versions,
        llm=llm,
        embeddings=embeddings,
        vector_store=vector_store,
    )
