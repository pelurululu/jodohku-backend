"""
JODOHKU.MY — Chat & Messaging Models
Controlled chat system with strike enforcement
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime,
    ForeignKey, Enum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class ConversationStatus(str, enum.Enum):
    PENDING = "pending"       # Lamar sent, awaiting reply
    ACTIVE = "active"         # Both parties engaged
    EXPIRED = "expired"       # Grace period ended
    BLOCKED = "blocked"       # One party blocked
    CLOSED = "closed"         # Subscription expired / manually closed


class MessageStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    BLOCKED = "blocked"       # Caught by content filter


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Initiator (who pressed Lamar)
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    # Recipient
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=True
    )
    
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.PENDING
    )
    
    # Message counts for tier enforcement
    message_count_initiator: Mapped[int] = mapped_column(Integer, default=0)
    message_count_recipient: Mapped[int] = mapped_column(Integer, default=0)
    
    # WhatsApp sharing status
    whatsapp_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    whatsapp_requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_conv_initiator", "initiator_id", "status"),
        Index("idx_conv_recipient", "recipient_id", "status"),
        Index("idx_conv_last_msg", "last_message_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Text only — no file/image uploads in chat
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus), default=MessageStatus.SENT
    )
    
    # If blocked by content filter, reason stored here
    blocked_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Was this an ice-breaker message?
    is_ice_breaker: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_msg_conv", "conversation_id", "created_at"),
        Index("idx_msg_sender", "sender_id"),
    )


class IceBreaker(Base):
    """Pre-defined ice-breaker phrases for initiating conversation."""
    __tablename__ = "ice_breakers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    text_ms: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
