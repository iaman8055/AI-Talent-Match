import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from src.application.ai.ports import RerankerClient, VectorStore
from src.application.auth.ports import (
    AccessTokenService,
    EmailSender,
    GoogleOAuthClient,
    PasswordHasher,
)
from src.application.auth.service import AuthService
from src.application.candidate.ports import ResumeProcessingDispatcher, StorageClient
from src.application.candidate.service import CandidateService
from src.application.company.service import CompanyService
from src.application.job.ports import JobProcessingDispatcher
from src.application.job.service import JobService
from src.application.matching.ports import MatchingDispatcher
from src.application.matching.service import MatchingService
from src.core.config import Settings, get_settings
from src.domain.candidate.repository import CandidateRepository, ResumeRepository
from src.domain.company.entities import CompanyMember, CompanyMemberRole
from src.domain.company.repository import CompanyRepository
from src.domain.job.entities import Job
from src.domain.job.repository import JobRepository, JobVersionRepository
from src.domain.matching.repository import MatchScoreRepository
from src.domain.user.entities import User, UserRole
from src.domain.user.repository import (
    EmailVerificationTokenRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
    UserRepository,
)
from src.infrastructure.ai.llm_reranker_client import LLMRerankerClient
from src.infrastructure.ai.ollama_client import OllamaClient
from src.infrastructure.db.repositories import (
    SqlAlchemyCandidateRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyEmailVerificationTokenRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyJobVersionRepository,
    SqlAlchemyMatchScoreRepository,
    SqlAlchemyPasswordResetTokenRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyResumeRepository,
    SqlAlchemyUserRepository,
)
from src.infrastructure.db.session import get_db
from src.infrastructure.notifications.email.celery_email_sender import CeleryEmailSender
from src.infrastructure.oauth.google_oauth_client import (
    GoogleOAuthClient as ConcreteGoogleOAuthClient,
)
from src.infrastructure.security.jwt_service import JWTTokenService
from src.infrastructure.security.password_hasher import Argon2PasswordHasher
from src.infrastructure.storage.s3_client import S3StorageClient
from src.infrastructure.tasks.job_tasks import CeleryJobDispatcher
from src.infrastructure.tasks.matching_tasks import CeleryMatchingDispatcher
from src.infrastructure.tasks.resume_tasks import CeleryResumeDispatcher
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore

_bearer_scheme = HTTPBearer(auto_error=False)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(db)


def get_refresh_token_repository(db: Session = Depends(get_db)) -> RefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(db)


def get_email_verification_repository(
    db: Session = Depends(get_db),
) -> EmailVerificationTokenRepository:
    return SqlAlchemyEmailVerificationTokenRepository(db)


def get_password_reset_repository(db: Session = Depends(get_db)) -> PasswordResetTokenRepository:
    return SqlAlchemyPasswordResetTokenRepository(db)


def get_company_repository(db: Session = Depends(get_db)) -> CompanyRepository:
    return SqlAlchemyCompanyRepository(db)


def get_password_hasher() -> PasswordHasher:
    return Argon2PasswordHasher()


def get_access_token_service(settings: Settings = Depends(get_settings)) -> AccessTokenService:
    return JWTTokenService(settings.jwt_secret_key, settings.jwt_access_token_expire_minutes)


def get_email_sender(settings: Settings = Depends(get_settings)) -> EmailSender:
    return CeleryEmailSender(settings.frontend_url)


def get_google_oauth_client(settings: Settings = Depends(get_settings)) -> GoogleOAuthClient | None:
    if not (
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_oauth_redirect_uri
    ):
        return None
    return ConcreteGoogleOAuthClient(
        settings.google_client_id, settings.google_client_secret, settings.google_oauth_redirect_uri
    )


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repository),
    refresh_token_repo: RefreshTokenRepository = Depends(get_refresh_token_repository),
    email_verification_repo: EmailVerificationTokenRepository = Depends(
        get_email_verification_repository
    ),
    password_reset_repo: PasswordResetTokenRepository = Depends(get_password_reset_repository),
    company_repo: CompanyRepository = Depends(get_company_repository),
    password_hasher: PasswordHasher = Depends(get_password_hasher),
    access_token_service: AccessTokenService = Depends(get_access_token_service),
    email_sender: EmailSender = Depends(get_email_sender),
    google_oauth_client: GoogleOAuthClient | None = Depends(get_google_oauth_client),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(
        user_repo=user_repo,
        refresh_token_repo=refresh_token_repo,
        email_verification_repo=email_verification_repo,
        password_reset_repo=password_reset_repo,
        company_repo=company_repo,
        password_hasher=password_hasher,
        access_token_service=access_token_service,
        email_sender=email_sender,
        refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
        google_oauth_client=google_oauth_client,
    )


def get_company_service(
    company_repo: CompanyRepository = Depends(get_company_repository),
    email_sender: EmailSender = Depends(get_email_sender),
) -> CompanyService:
    return CompanyService(company_repo, email_sender)


def get_candidate_repository(db: Session = Depends(get_db)) -> CandidateRepository:
    return SqlAlchemyCandidateRepository(db)


def get_resume_repository(db: Session = Depends(get_db)) -> ResumeRepository:
    return SqlAlchemyResumeRepository(db)


def get_storage_client(settings: Settings = Depends(get_settings)) -> StorageClient:
    return S3StorageClient(
        bucket=settings.supabase_storage_bucket,
        endpoint_url=settings.supabase_s3_endpoint_url,
        access_key_id=settings.supabase_s3_access_key_id,
        secret_access_key=settings.supabase_s3_secret_access_key,
        region=settings.supabase_s3_region,
    )


def get_resume_dispatcher() -> ResumeProcessingDispatcher:
    return CeleryResumeDispatcher()


def get_candidate_service(
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    storage: StorageClient = Depends(get_storage_client),
    dispatcher: ResumeProcessingDispatcher = Depends(get_resume_dispatcher),
) -> CandidateService:
    return CandidateService(candidate_repo, resume_repo, storage, dispatcher)


def get_job_repository(db: Session = Depends(get_db)) -> JobRepository:
    return SqlAlchemyJobRepository(db)


def get_job_version_repository(db: Session = Depends(get_db)) -> JobVersionRepository:
    return SqlAlchemyJobVersionRepository(db)


def get_job_dispatcher() -> JobProcessingDispatcher:
    return CeleryJobDispatcher()


def get_job_service(
    job_repo: JobRepository = Depends(get_job_repository),
    dispatcher: JobProcessingDispatcher = Depends(get_job_dispatcher),
) -> JobService:
    return JobService(job_repo, dispatcher)


def require_job_membership(*roles: CompanyMemberRole) -> Callable[..., Job]:
    def dependency(
        job_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        job_repo: JobRepository = Depends(get_job_repository),
        company_repo: CompanyRepository = Depends(get_company_repository),
    ) -> Job:
        job = job_repo.get_by_id(job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
        member = company_repo.get_member(job.company_id, current_user.id)
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this company")
        if roles and member.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Insufficient permissions in this company"
            )
        return job

    return dependency


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    return QdrantVectorStore(settings.qdrant_url)


def get_reranker_client(settings: Settings = Depends(get_settings)) -> RerankerClient:
    llm_client = OllamaClient(
        base_url=settings.ollama_base_url,
        api_key=settings.ollama_api_key,
        llm_model=settings.ollama_llm_model,
        embedding_model=settings.ollama_embedding_model,
    )
    return LLMRerankerClient(llm_client)


def get_match_score_repository(db: Session = Depends(get_db)) -> MatchScoreRepository:
    return SqlAlchemyMatchScoreRepository(db)


def get_matching_dispatcher() -> MatchingDispatcher:
    return CeleryMatchingDispatcher()


def get_matching_service(
    candidate_repo: CandidateRepository = Depends(get_candidate_repository),
    resume_repo: ResumeRepository = Depends(get_resume_repository),
    job_repo: JobRepository = Depends(get_job_repository),
    company_repo: CompanyRepository = Depends(get_company_repository),
    match_score_repo: MatchScoreRepository = Depends(get_match_score_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    reranker: RerankerClient = Depends(get_reranker_client),
) -> MatchingService:
    return MatchingService(
        candidate_repo,
        resume_repo,
        job_repo,
        company_repo,
        match_score_repo,
        vector_store,
        reranker,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
    access_token_service: AccessTokenService = Depends(get_access_token_service),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    try:
        claims = access_token_service.decode(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token"
        ) from exc

    user = user_repo.get_by_id(claims.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access token")

    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return current_user

    return dependency


def require_company_role(*roles: CompanyMemberRole) -> Callable[..., CompanyMember]:
    def dependency(
        company_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        company_repo: CompanyRepository = Depends(get_company_repository),
    ) -> CompanyMember:
        member = company_repo.get_member(company_id, current_user.id)
        if member is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a member of this company")
        if roles and member.role not in roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Insufficient permissions in this company"
            )
        return member

    return dependency
