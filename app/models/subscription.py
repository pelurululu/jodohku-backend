"""
JODOHKU.MY — Subscription & Payment Models
Tiered subscription with failover payment gateways
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, Index, Numeric
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base
from app.models.user import SubscriptionTier


class PaymentGateway(str, enum.Enum):
    TOYYIBPAY = "toyyibpay"
    BILLPLZ = "billplz"
    SENANGPAY = "senangpay"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class TransactionType(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    RENEWAL = "renewal"
    UPGRADE = "upgrade"
    REFUND = "refund"


# ─── Tier Configuration (reference table) ───

class TierConfig(Base):
    __tablename__ = "tier_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), unique=True, nullable=False
    )

    # Pricing
    price_myr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)

    # Limits
    daily_profile_views: Mapped[int] = mapped_column(Integer, default=10)
    max_concurrent_chats: Mapped[int] = mapped_column(Integer, default=3)
    max_messages_per_chat: Mapped[int] = mapped_column(Integer, default=10)
    whatsapp_requests_per_day: Mapped[int] = mapped_column(Integer, default=0)
    golden_tickets_per_month: Mapped[int] = mapped_column(Integer, default=0)

    # Feature flags
    has_clear_photos: Mapped[bool] = mapped_column(Boolean, default=False)
    has_whatsapp_access: Mapped[bool] = mapped_column(Boolean, default=False)
    has_priority_search: Mapped[bool] = mapped_column(Boolean, default=False)
    has_invisible_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video_taaruf: Mapped[bool] = mapped_column(Boolean, default=False)
    has_human_matchmaker: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ctos_check: Mapped[bool] = mapped_column(Boolean, default=False)
    has_monthly_report: Mapped[bool] = mapped_column(Boolean, default=False)
    has_ads_free: Mapped[bool] = mapped_column(Boolean, default=False)
    has_beta_features: Mapped[bool] = mapped_column(Boolean, default=False)

    # Display
    badge_label: Mapped[str] = mapped_column(String(50), nullable=False)
    badge_color: Mapped[str] = mapped_column(String(7), nullable=False)  # hex

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


# ─── Subscription ───

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), nullable=False
    )

    # Subscription window
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    grace_period_ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Payment reference
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False)

    # Promo / discount applied
    promo_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    discount_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Refund eligibility
    refund_eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    conversations_started: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="subscriptions")

    __table_args__ = (
        Index("idx_sub_user_active", "user_id", "is_active"),
        Index("idx_sub_expires", "expires_at"),
    )


# ─── Transaction ───

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True  # Nullable for anonymization after deletion
    )

    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType), nullable=False
    )

    # Amount
    amount_myr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    discount_applied: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    final_amount_myr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Gateway
    gateway: Mapped[PaymentGateway] = mapped_column(
        Enum(PaymentGateway), nullable=False
    )
    gateway_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway_bill_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING
    )

    # FIX: renamed from 'metadata' (reserved by SQLAlchemy) to 'payment_metadata'
    payment_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # LHDN retention: kept 7 years, anonymized after user deletion
    is_anonymized: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_txn_user", "user_id", "created_at"),
        Index("idx_txn_status", "status"),
        Index("idx_txn_gateway_ref", "gateway_reference"),
    )


# ─── Golden Ticket Referral ───

class GoldenTicket(Base):
    __tablename__ = "golden_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Who generated the ticket
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Unique referral code
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Who used it (null if unused)
    redeemed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    is_redeemed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Month this ticket belongs to (for monthly quota tracking)
    issued_month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2025-06"

    # Reward given to owner after redemption
    reward_applied: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ticket_owner_month", "owner_id", "issued_month"),
    )
