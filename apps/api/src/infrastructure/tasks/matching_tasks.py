import uuid

from sqlalchemy.orm import Session

from src.application.matching.service import MatchingService
from src.core.config import get_settings
from src.infrastructure.ai.llm_reranker_client import LLMRerankerClient
from src.infrastructure.ai.ollama_client import OllamaClient
from src.infrastructure.db.repositories import (
    SqlAlchemyCandidateRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMatchScoreRepository,
    SqlAlchemyResumeRepository,
)
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.tasks.celery_app import celery_app
from src.infrastructure.tasks.recruiter_agent_tasks import CeleryRecruiterAgentDispatcher
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
_reranker = LLMRerankerClient(_llm_client)
_vector_store = QdrantVectorStore(settings.qdrant_url)
_recruiter_agent_dispatcher = CeleryRecruiterAgentDispatcher()

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 3,
}


def _build_matching_service(session: Session) -> MatchingService:
    return MatchingService(
        candidate_repo=SqlAlchemyCandidateRepository(session),
        resume_repo=SqlAlchemyResumeRepository(session),
        job_repo=SqlAlchemyJobRepository(session),
        company_repo=SqlAlchemyCompanyRepository(session),
        match_score_repo=SqlAlchemyMatchScoreRepository(session),
        vector_store=_vector_store,
        reranker=_reranker,
        recruiter_agent_dispatcher=_recruiter_agent_dispatcher,
    )


@celery_app.task(name="compute_job_matches", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def compute_job_matches_task(job_id: str) -> None:
    session = SessionLocal()
    try:
        _build_matching_service(session).compute_matches_for_job(uuid.UUID(job_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@celery_app.task(name="compute_candidate_matches", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def compute_candidate_matches_task(candidate_id: str) -> None:
    session = SessionLocal()
    try:
        _build_matching_service(session).compute_matches_for_candidate(uuid.UUID(candidate_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CeleryMatchingDispatcher:
    """Implements the application layer's MatchingDispatcher port."""

    def dispatch_compute_for_candidate(self, candidate_id: uuid.UUID) -> None:
        compute_candidate_matches_task.delay(str(candidate_id))

    def dispatch_compute_for_job(self, job_id: uuid.UUID) -> None:
        compute_job_matches_task.delay(str(job_id))
