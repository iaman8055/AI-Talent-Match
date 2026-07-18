import logging

logger = logging.getLogger(__name__)


class ConsoleEmailProvider:
    """Logs email content instead of sending it.

    Swap point for a real provider (Postmark/SES/Resend): implement EmailProvider
    and change the instantiation in infrastructure/tasks/email_tasks.py — nothing
    else in the call chain needs to change.
    """

    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("email to=%s subject=%s\n%s", to, subject, body)
