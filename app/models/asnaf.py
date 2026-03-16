"""
JODOHKU.MY — Asnaf Access Models
Hidden pathway for asnaf users verified by JAKIM/MAIWP
Data stored in separate partition, no cross-referencing
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class AsnafCategory(str, enum.Enum):
    FAKIR = "fakir"
    MISKIN = "miskin"
    AMIL = "amil"
    MUALLAF = "muallaf"
    RIQAB = "riqab"
    GHARIMIN = "gharimin"
    FISABILILLAH = "fisabilillah"
    IBNU_SABIL = "ibnu_sabil"


class AsnafStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class AsnafApplication(Base):
    __tablename__ = "asnaf_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    category: Mapped[AsnafCategory] = mapped_column(
        Enum(AsnafCategory), nullable=False
    )
    
    # Verification document path (encrypted)
    document_path: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Referring agency
    agency_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    agency_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    status: Mapped[AsnafStatus] = mapped_column(
        Enum(AsnafStatus), default=AsnafStatus.PENDING
    )
    
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AsnafVerification(Base):
    """Active asnaf status with expiry tracking."""
    __tablename__ = "asnaf_verifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    
    category: Mapped[AsnafCategory] = mapped_column(
        Enum(AsnafCategory), nullable=False
    )
    
    # 30-day free access, then RM9.99/month billed to agency
    free_access_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Agency billing
    agency_sponsored: Mapped[bool] = mapped_column(Boolean, default=False)
    monthly_rate_myr: Mapped[float] = mapped_column(default=9.99)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
