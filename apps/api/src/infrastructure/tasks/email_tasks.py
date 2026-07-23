import uuid
from datetime import UTC, datetime

from src.domain.notifications.entities import NotificationDelivery, NotificationDeliveryStatus
from src.infrastructure.db.repositories import SqlAlchemyNotificationDeliveryRepository
from src.infrastructure.db.session import SessionLocal
from src.infrastructure.notifications.email.console_provider import ConsoleEmailProvider
from src.infrastructure.tasks.celery_app import celery_app

_email_provider = ConsoleEmailProvider()


@celery_app.task(name="send_email")  # type: ignore[untyped-decorator]
def send_email_task(to: str, subject: str, body: str) -> None:
    """Every email in the app funnels through this one task — wrapping it here gives every send
    an audit row in `notification_deliveries` without touching any of the individual call sites
    (verification, password reset, company invite, candidate invite, outreach)."""
    error_message: str | None = None
    try:
        _email_provider.send(to, subject, body)
        status = NotificationDeliveryStatus.SENT
    except Exception as exc:
        status = NotificationDeliveryStatus.FAILED
        error_message = str(exc)[:500]
        raise
    finally:
        session = SessionLocal()
        try:
            SqlAlchemyNotificationDeliveryRepository(session).add(
                NotificationDelivery(
                    id=uuid.uuid4(),
                    to_email=to,
                    subject=subject,
                    status=status,
                    error_message=error_message,
                    created_at=datetime.now(UTC),
                )
            )
            session.commit()
        finally:
            session.close()
