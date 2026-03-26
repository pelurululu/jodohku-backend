"""
JODOHKU.MY — Notification Routes
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.notification_service import NotificationService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
async def get_notifications(
    page: int = Query(1, ge=1),
    unread_only: bool = False,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    return await service.get_notifications(current_user.id, page, unread_only)


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    await service.mark_read(current_user.id, notification_id)
    return {"status": "read"}


@router.post("/read-all")
async def mark_all_as_read(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    await service.mark_all_read(current_user.id)
    return {"status": "all_read"}


@router.get("/unread-count")
async def get_unread_count(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return {"unread_count": count}


@router.put("/preferences")
async def update_notification_preferences(
    preferences: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = NotificationService(db)
    await service.update_preferences(current_user.id, preferences)
    return {"message": "Keutamaan notifikasi dikemaskini."}


@router.post("/send")
async def send_notification(
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a notification to another user. Used by lamar flow."""
    body = await request.json()
    from uuid import UUID as _UUID
    recipient_id = body.get("recipient_user_id")
    if not recipient_id:
        return {"status": "skipped"}
    service = NotificationService(db)
    await service.create_notification(
        user_id=_UUID(str(recipient_id)),
        notif_type=body.get("type", "lamar_received"),
        title=body.get("title", "Notifikasi baharu"),
        body=body.get("body", ""),
    )
    return {"status": "sent"}
