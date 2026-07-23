from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.orm import Session

from src.agents.apply_agent.graph import ApplyAgentDeps, ApplyAgentState, compile_apply_agent_graph
from src.application.applications.service import ApplicationService
from src.application.notifications.service import NotificationService
from src.core.config import get_settings
from src.infrastructure.db.repositories import (
    SqlAlchemyAgentConfigRepository,
    SqlAlchemyAgentDecisionRepository,
    SqlAlchemyApplicationRepository,
    SqlAlchemyCandidateRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyJobRepository,
    SqlAlchemyMatchScoreRepository,
    SqlAlchemyNotificationRepository,
    SqlAlchemyUserRepository,
)
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.notifications.email.celery_email_sender import CeleryEmailSender
from src.infrastructure.tasks.celery_app import celery_app

settings = get_settings()

# psycopg (unlike SQLAlchemy) wants a bare "postgresql://" DSN, not the "+psycopg" driver spec.
_CHECKPOINTER_DSN = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

_RETRY_KWARGS = {
    "autoretry_for": (Exception,),
    "retry_backoff": True,
    "retry_backoff_max": 300,
    "retry_jitter": True,
    "max_retries": 3,
}


def _build_deps(session: Session) -> ApplyAgentDeps:
    notification_service = NotificationService(SqlAlchemyNotificationRepository(session))
    return ApplyAgentDeps(
        agent_config_repo=SqlAlchemyAgentConfigRepository(session),
        agent_decision_repo=SqlAlchemyAgentDecisionRepository(session),
        match_score_repo=SqlAlchemyMatchScoreRepository(session),
        job_repo=SqlAlchemyJobRepository(session),
        candidate_repo=SqlAlchemyCandidateRepository(session),
        notification_service=notification_service,
        application_service=ApplicationService(
            application_repo=SqlAlchemyApplicationRepository(session),
            job_repo=SqlAlchemyJobRepository(session),
            candidate_repo=SqlAlchemyCandidateRepository(session),
            user_repo=SqlAlchemyUserRepository(session),
            company_repo=SqlAlchemyCompanyRepository(session),
            email_sender=CeleryEmailSender(settings.frontend_url),
            notification_service=notification_service,
        ),
    )


@celery_app.task(name="run_apply_agent_scan", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def run_apply_agent_scan_task() -> None:
    """Celery Beat entry (every 15 min, see celery_app.py). Fans out one task per candidate with
    auto-apply enabled rather than evaluating everyone in a single long-running task."""
    session = SessionLocal()
    try:
        config_repo = SqlAlchemyAgentConfigRepository(session)
        candidate_ids = [config.candidate_id for config in config_repo.list_auto_apply_enabled()]
    finally:
        session.close()

    for candidate_id in candidate_ids:
        run_apply_agent_for_candidate_task.delay(str(candidate_id))


@celery_app.task(name="run_apply_agent_for_candidate", **_RETRY_KWARGS)  # type: ignore[untyped-decorator]
def run_apply_agent_for_candidate_task(candidate_id: str) -> None:
    session = SessionLocal()
    try:
        deps = _build_deps(session)
        with PostgresSaver.from_conn_string(_CHECKPOINTER_DSN) as checkpointer:
            checkpointer.setup()  # idempotent — creates LangGraph's own tables on first run
            graph = compile_apply_agent_graph(deps, checkpointer)
            initial_state: ApplyAgentState = {
                "candidate_id": candidate_id,
                "should_run": False,
                "min_match_score": 0,
                "daily_apply_cap": 0,
                "pending": [],
                "constraint_results": {},
                "plan": [],
                "decisions": [],
            }
            graph.invoke(
                initial_state,
                config={"configurable": {"thread_id": f"apply-agent:{candidate_id}"}},
            )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
