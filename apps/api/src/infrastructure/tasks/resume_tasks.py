import uuid

from sqlalchemy.orm import Session

from src.application.candidate.parsing_service import ResumeParsingService
from src.core.config import get_settings
from src.infrastructure.ai.nvidia_client import NvidiaClient
from src.infrastructure.db.repositories import (
    SqlAlchemyCandidateRepository,
    SqlAlchemyResumeRepository,
)
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.parsing.text_extraction import DocumentTextExtractor
from src.infrastructure.storage.s3_client import S3StorageClient
from src.infrastructure.tasks.celery_app import celery_app
from src.infrastructure.tasks.matching_tasks import CeleryMatchingDispatcher
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore

settings = get_settings()

# Stateless HTTP/API wrapper clients — safe to share across task invocations. Only the DB
# session is created fresh per task (SQLAlchemy sessions aren't safe to share across calls).
_text_extractor = DocumentTextExtractor()
_llm_client = NvidiaClient(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key,
    llm_model=settings.nvidia_llm_model,
    embedding_model=settings.nvidia_embedding_model,
)
_storage = S3StorageClient(
    bucket=settings.supabase_storage_bucket,
    endpoint_url=settings.supabase_s3_endpoint_url,
    access_key_id=settings.supabase_s3_access_key_id,
    secret_access_key=settings.supabase_s3_secret_access_key,
    region=settings.supabase_s3_region,
)
_vector_store = QdrantVectorStore(settings.qdrant_url, settings.qdrant_api_key)
_matching_dispatcher = CeleryMatchingDispatcher()

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 3,
}


def _build_parsing_service(session: Session) -> ResumeParsingService:
    return ResumeParsingService(
        candidate_repo=SqlAlchemyCandidateRepository(session),
        resume_repo=SqlAlchemyResumeRepository(session),
        storage=_storage,
        text_extractor=_text_extractor,
        llm_client=_llm_client,
        embedding_client=_llm_client,
        vector_store=_vector_store,
        matching_dispatcher=_matching_dispatcher,
    )


@celery_app.task(name="parse_resume", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def parse_resume_task(resume_id: str) -> None:
    session = SessionLocal()
    try:
        _build_parsing_service(session).parse_resume(uuid.UUID(resume_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    embed_resume_task.delay(resume_id)


@celery_app.task(name="embed_resume", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def embed_resume_task(resume_id: str) -> None:
    session = SessionLocal()
    try:
        _build_parsing_service(session).embed_resume(uuid.UUID(resume_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CeleryResumeDispatcher:
    """Implements the application layer's ResumeProcessingDispatcher port."""

    def dispatch_parse(self, resume_id: uuid.UUID) -> None:
        parse_resume_task.delay(str(resume_id))
