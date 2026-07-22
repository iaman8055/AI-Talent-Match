import uuid

from src.domain.company.entities import CompanyInvite
from src.domain.user.entities import User
from src.infrastructure.tasks.email_tasks import send_email_task


class CeleryEmailSender:
    """Implements the application layer's EmailSender port by enqueueing a Celery
    task per message, so a slow/unavailable email provider never blocks a request."""

    def __init__(self, frontend_url: str) -> None:
        self._frontend_url = frontend_url

    def send_verification_email(self, user: User, raw_token: str) -> None:
        link = f"{self._frontend_url}/verify-email?token={raw_token}"
        send_email_task.delay(
            user.email,
            "Verify your email",
            f"Hi {user.full_name},\n\nVerify your email: {link}\n",
        )

    def send_password_reset_email(self, user: User, raw_token: str) -> None:
        link = f"{self._frontend_url}/reset-password?token={raw_token}"
        send_email_task.delay(
            user.email,
            "Reset your password",
            f"Hi {user.full_name},\n\nReset your password: {link}\n",
        )

    def send_invite_email(self, invite: CompanyInvite, company_name: str, raw_token: str) -> None:
        link = f"{self._frontend_url}/accept-invite?token={raw_token}"
        send_email_task.delay(
            invite.email,
            f"You're invited to join {company_name}",
            f"You've been invited to join {company_name} on AI Talent Match: {link}\n",
        )

    def send_candidate_invite_email(
        self, candidate_user: User, job_id: uuid.UUID, job_title: str, company_name: str
    ) -> None:
        link = f"{self._frontend_url}/jobs/{job_id}"
        send_email_task.delay(
            candidate_user.email,
            f"{company_name} invited you to apply for {job_title}",
            (
                f"Hi {candidate_user.full_name},\n\n{company_name} thinks you'd be a great fit "
                f"for {job_title}. View the role: {link}\n"
            ),
        )

    def send_outreach_email(self, candidate_user: User, subject: str, body: str) -> None:
        send_email_task.delay(candidate_user.email, subject, body)
