"""
JODOHKU.MY — Notification Service
Real implementation reading/writing from database
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType, NotificationPreference


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_notifications(self, user_id: UUID, page: int, unread_only: bool) -> dict:
        offset = (page - 1) * 20
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)
        query = query.order_by(desc(Notification.created_at)).offset(offset).limit(20)

        result = await self.db.execute(query)
        notifications = result.scalars().all()

        count_q = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
        total = (await self.db.execute(count_q)).scalar() or 0

        return {
            "notifications": [self._format(n) for n in notifications],
            "total": total,
            "page": page,
            "unread_count": await self.get_unread_count(user_id),
        }

    async def mark_read(self, user_id: UUID, notification_id: UUID):
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        notif = result.scalar_one_or_none()
        if notif and not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.utcnow()
            await self.db.flush()

    async def mark_all_read(self, user_id: UUID):
        await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True, read_at=datetime.utcnow())
        )
        await self.db.flush()

    async def get_unread_count(self, user_id: UUID) -> int:
        q = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read == False
        )
        return (await self.db.execute(q)).scalar() or 0

    async def update_preferences(self, user_id: UUID, preferences: dict):
        result = await self.db.execute(
            select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        )
        prefs = result.scalar_one_or_none()
        if not prefs:
            prefs = NotificationPreference(user_id=user_id)
            self.db.add(prefs)
        for key, val in preferences.items():
            if hasattr(prefs, key):
                setattr(prefs, key, val)
        await self.db.flush()

    async def send_notification(
        self, user_id: UUID, type: str, title_ms: str, title_en: str,
        body_ms: str, body_en: str, data: dict = None, action_url: str = None
    ):
        notif = Notification(
            user_id=user_id,
            type=NotificationType(type),
            title_ms=title_ms,
            title_en=title_en,
            body_ms=body_ms,
            body_en=body_en,
            action_url=action_url,
            data=data or {},
        )
        self.db.add(notif)
        await self.db.flush()
        return notif

    def _format(self, n: Notification) -> dict:
        return {
            "id": str(n.id),
            "type": n.type.value,
            "title": n.title_ms,
            "body": n.body_ms,
            "action_url": n.action_url,
            "is_read": n.is_read,
            "data": n.data,
            "created_at": n.created_at.isoformat(),
            "read_at": n.read_at.isoformat() if n.read_at else None,
        }
