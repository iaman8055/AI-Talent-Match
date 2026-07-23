import uuid
from datetime import datetime

from pydantic import BaseModel

from src.domain.notifications.entities import Notification, NotificationType


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime

    @classmethod
    def from_entity(cls, notification: Notification) -> "NotificationResponse":
        return cls(
            id=notification.id,
            type=notification.type,
            title=notification.title,
            body=notification.body,
            link=notification.link,
            read_at=notification.read_at,
            created_at=notification.created_at,
        )


class UnreadCountResponse(BaseModel):
    count: int
