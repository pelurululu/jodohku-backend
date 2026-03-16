"""
JODOHKU.MY — Admin & Enforcement Models
God Mode dashboard, reports, strikes, audit trail
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime,
    ForeignKey, Enum, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class AdminRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    SUPPORT = "support"


class ReportCategory(str, enum.Enum):
    FAKE_PROFILE = "fake_profile"
    OBSCENE_CONTENT = "obscene_content"
    FINANCIAL_SCAM = "financial_scam"
    HARASSMENT = "harassment"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[AdminRole] = mapped_column(Enum(AdminRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reported_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    category: Mapped[ReportCategory] = mapped_column(
        Enum(ReportCategory), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Evidence (screenshot URLs, message IDs)
    evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus), default=ReportStatus.PENDING
    )
    
    # Admin handling
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_report_status", "status", "created_at"),
        Index("idx_report_target", "reported_user_id"),
    )


class StrikeRecord(Base):
    __tablename__ = "strike_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    strike_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, or 3
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    
    # The message or action that triggered the strike
    trigger_message_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    trigger_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Auto-suspension details (Strike 3)
    suspension_starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    suspension_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Appeal
    appeal_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    appeal_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    appeal_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_strike_user", "user_id"),
    )


class AuditLog(Base):
    """PDPA compliance: every admin action is logged."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True
    )
    
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_audit_admin", "admin_id", "created_at"),
        Index("idx_audit_entity", "entity_type", "entity_id"),
    )
