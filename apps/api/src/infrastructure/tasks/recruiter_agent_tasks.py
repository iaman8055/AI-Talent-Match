import uuid

from sqlalchemy.orm import Session

from src.agents.recruiter_agent.graph import RecruiterAgentDeps, build_recruiter_agent_graph
from src.application.notifications.service import NotificationService
from src.core.config import get_settings
from src.infrastructure.ai.nvidia_client import NvidiaClient
from src.infrastructure.db.repositories import (
    SqlAlchemyCandidateRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMatchScoreRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyOutreachDraftRepository,
)
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.tasks.celery_app import celery_app

settings = get_settings()

# Stateless HTTP wrapper client — safe to share across task invocations, same pattern as every
# other Celery task module in this app.
_llm_client = NvidiaClient(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key,
    llm_model=settings.nvidia_llm_model,
    embedding_model=settings.nvidia_embedding_model,
)

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 3,
}


def _build_deps(session: Session) -> RecruiterAgentDeps:
    return RecruiterAgentDeps(
        candidate_repo=SqlAlchemyCandidateRepository(session),
        job_repo=SqlAlchemyJobRepository(session),
        company_repo=SqlAlchemyCompanyRepository(session),
        match_score_repo=SqlAlchemyMatchScoreRepository(session),
        outreach_draft_repo=SqlAlchemyOutreachDraftRepository(session),
        notification_service=NotificationService(SqlAlchemyNotificationRepository(session)),
        llm_client=_llm_client,
    )


@celery_app.task(name="run_recruiter_agent_for_candidate", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def run_recruiter_agent_for_candidate_task(candidate_id: str) -> None:
    session = SessionLocal()
    try:
        deps = _build_deps(session)
        graph = build_recruiter_agent_graph(deps).compile()
        graph.invoke(
            {
                "candidate_id": candidate_id,
                "should_run": False,
                "pending": [],
                "generated": [],
            }
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class CeleryRecruiterAgentDispatcher:
    """Implements the application layer's RecruiterAgentDispatcher port."""

    def dispatch_for_candidate(self, candidate_id: uuid.UUID) -> None:
        run_recruiter_agent_for_candidate_task.delay(str(candidate_id))
