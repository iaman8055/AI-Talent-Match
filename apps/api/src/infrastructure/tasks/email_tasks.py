from src.infrastructure.notifications.email.console_provider import ConsoleEmailProvider
from src.infrastructure.tasks.celery_app import celery_app

_email_provider = ConsoleEmailProvider()


@celery_app.task(name="send_email")  # type: ignore[untyped-decorator]
def send_email_task(to: str, subject: str, body: str) -> None:
    _email_provider.send(to, subject, body)
