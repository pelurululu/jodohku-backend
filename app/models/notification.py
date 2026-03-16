"""
JODOHKU.MY — Notification Models
Omnichannel push: WebSocket + FCM + Email
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class NotificationType(str, enum.Enum):
    NEW_MESSAGE = "new_message"
    NEW_MATCH = "new_match"
    PROFILE_VIEWED = "profile_viewed"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    WHATSAPP_REQUEST = "whatsapp_request"
    WHATSAPP_APPROVED = "whatsapp_approved"
    STRIKE_WARNING = "strike_warning"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    WALI_INVITATION = "wali_invitation"
    GOLDEN_TICKET = "golden_ticket"
    BADGE_EARNED = "badge_earned"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False
    )
    
    title_ms: Mapped[str] = mapped_column(String(255), nullable=False)
    title_en: Mapped[str] = mapped_column(String(255), nullable=False)
    body_ms: Mapped[str] = mapped_column(Text, nullable=False)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Action URL or deep link
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Extra data payload
    data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Delivery channels used
    sent_websocket: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_fcm: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="notifications")

    __table_args__ = (
        Index("idx_notif_user_read", "user_id", "is_read", "created_at"),
    )


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    
    enable_new_message: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_new_match: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_profile_viewed: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_subscription: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_system: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Channel preferences
    prefer_email: Mapped[bool] = mapped_column(Boolean, default=True)
    prefer_push: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Quiet hours (no push notifications)
    quiet_start_hour: Mapped[Optional[int]] = mapped_column(default=23)  # 11 PM
    quiet_end_hour: Mapped[Optional[int]] = mapped_column(default=7)     # 7 AM
