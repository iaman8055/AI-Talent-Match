import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class NotificationType(StrEnum):
    CANDIDATE_INVITED = "candidate_invited"
    APPLICATION_STATUS_CHANGED = "application_status_changed"
    AUTO_APPLIED = "auto_applied"
    NEW_OUTREACH_DRAFT = "new_outreach_draft"


@dataclass
class Notification:
    id: uuid.UUID
    user_id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationDeliveryStatus(StrEnum):
    SENT = "sent"
    FAILED = "failed"


@dataclass
class NotificationDelivery:
    id: uuid.UUID
    to_email: str
    subject: str
    status: NotificationDeliveryStatus
    error_message: str | None
    created_at: datetime
