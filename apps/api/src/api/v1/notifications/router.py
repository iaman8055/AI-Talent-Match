import uuid

from fastapi import APIRouter, Depends

from src.api.deps import get_current_user, get_notification_service
from src.api.v1.notifications.schemas import NotificationResponse, UnreadCountResponse
from src.application.notifications.service import NotificationService
from src.domain.user.entities import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> list[NotificationResponse]:
    notifications = notification_service.list_for_user(current_user.id)
    return [NotificationResponse.from_entity(n) for n in notifications]


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> UnreadCountResponse:
    return UnreadCountResponse(count=notification_service.unread_count(current_user.id))


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    notification = notification_service.mark_read(notification_id, current_user.id)
    return NotificationResponse.from_entity(notification)


@router.post("/read-all", status_code=204)
def mark_all_read(
    current_user: User = Depends(get_current_user),
    notification_service: NotificationService = Depends(get_notification_service),
) -> None:
    notification_service.mark_all_read(current_user.id)
