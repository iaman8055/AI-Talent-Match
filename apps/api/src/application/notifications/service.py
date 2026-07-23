import uuid
from datetime import UTC, datetime

from src.application.exceptions import NotFoundError
from src.domain.notifications.entities import Notification, NotificationType
from src.domain.notifications.repository import NotificationRepository


class NotificationService:
    """Purely synchronous persistence, no side effects — safe to call both from request-path
    code (the mark-read endpoints) and from Celery tasks/agents creating notifications."""

    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._notifications = notification_repo

    def notify(
        self,
        user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
        link: str | None = None,
    ) -> Notification:
        now = datetime.now(UTC)
        notification = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            link=link,
            read_at=None,
            created_at=now,
        )
        return self._notifications.add(notification)

    def list_for_user(self, user_id: uuid.UUID) -> list[Notification]:
        return self._notifications.list_for_user(user_id)

    def unread_count(self, user_id: uuid.UUID) -> int:
        return self._notifications.unread_count(user_id)

    def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
        notification = self._notifications.get_by_id(notification_id)
        if notification is None or notification.user_id != user_id:
            raise NotFoundError("Notification not found")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            notification = self._notifications.mark_read(notification)
        return notification

    def mark_all_read(self, user_id: uuid.UUID) -> None:
        self._notifications.mark_all_read(user_id)
