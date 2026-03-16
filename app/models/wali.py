"""
JODOHKU.MY — Wali/Mahram Mode Models
Unique feature: Guardian read-only access to matchmaking process
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class WaliRelation(str, enum.Enum):
    FATHER = "father"
    BROTHER = "brother"
    UNCLE = "uncle"
    GRANDFATHER = "grandfather"
    OTHER_MAHRAM = "other_mahram"


class WaliInvitation(Base):
    __tablename__ = "wali_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    wali_email: Mapped[str] = mapped_column(String(255), nullable=False)
    wali_name: Mapped[str] = mapped_column(String(100), nullable=False)
    relation: Mapped[WaliRelation] = mapped_column(Enum(WaliRelation), nullable=False)
    
    # Invitation token (sent via email)
    token: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    is_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class WaliAccess(Base):
    """Active wali observer accounts — read-only access."""
    __tablename__ = "wali_access"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    invitation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wali_invitations.id"),
        nullable=False
    )
    
    wali_email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_wali_user", "user_id"),
    )
