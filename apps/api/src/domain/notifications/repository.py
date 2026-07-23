import uuid
from typing import Protocol

from src.domain.notifications.entities import Notification, NotificationDelivery


class NotificationRepository(Protocol):
    def add(self, notification: Notification) -> Notification: ...

    def get_by_id(self, notification_id: uuid.UUID) -> Notification | None: ...

    def list_for_user(self, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
        """Newest first."""
        ...

    def unread_count(self, user_id: uuid.UUID) -> int: ...

    def mark_read(self, notification: Notification) -> Notification: ...

    def mark_all_read(self, user_id: uuid.UUID) -> None: ...


class NotificationDeliveryRepository(Protocol):
    def add(self, delivery: NotificationDelivery) -> NotificationDelivery: ...
