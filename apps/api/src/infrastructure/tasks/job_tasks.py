import uuid

from sqlalchemy.orm import Session

from src.application.job.parsing_service import JobParsingService
from src.core.config import get_settings
from src.infrastructure.ai.ollama_client import OllamaClient
from src.infrastructure.db.repositories import (
    SqlAlchemyJobRepository,
    SqlAlchemyJobVersionRepository,
)
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.tasks.celery_app import celery_app
from src.infrastructure.tasks.matching_tasks import CeleryMatchingDispatcher
from src.infrastructure.vector_store.qdrant_client import QdrantVectorStore

settings = get_settings()

# Stateless HTTP/API wrapper clients — safe to share across task invocations. Only the DB
# session is created fresh per task (SQLAlchemy sessions aren't safe to share across calls).
_llm_client = OllamaClient(
    base_url=settings.ollama_base_url,
    api_key=settings.ollama_api_key,
    llm_model=settings.ollama_llm_model,
    embedding_model=settings.ollama_embedding_model,
)
_vector_store = QdrantVectorStore(settings.qdrant_url)
_matching_dispatcher = CeleryMatchingDispatcher()

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 3,
}


def _build_parsing_service(session: Session) -> JobParsingService:
    return JobParsingService(
        job_repo=SqlAlchemyJobRepository(session),
        job_version_repo=SqlAlchemyJobVersionRepository(session),
        llm_client=_llm_client,
        embedding_client=_llm_client,
        vector_store=_vector_store,
        matching_dispatcher=_matching_dispatcher,
    )


@celery_app.task(name="parse_job", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def parse_job_task(job_id: str) -> None:
    session = SessionLocal()
    try:
        _build_parsing_service(session).parse_job(uuid.UUID(job_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

    embed_job_task.delay(job_id)


@celery_app.task(name="embed_job", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def embed_job_task(job_id: str) -> None:
    session = SessionLocal()
    try:
        _build_parsing_service(session).embed_job(uuid.UUID(job_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CeleryJobDispatcher:
    """Implements the application layer's JobProcessingDispatcher port."""

    def dispatch_parse(self, job_id: uuid.UUID) -> None:
        parse_job_task.delay(str(job_id))
