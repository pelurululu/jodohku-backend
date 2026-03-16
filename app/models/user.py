"""
JODOHKU.MY — User Models
Core user account, profile data, photos, and preference selections
"""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, Date, DateTime,
    ForeignKey, Enum, JSON, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
import enum

from app.database import Base


# ─── Enums ───

class Gender(str, enum.Enum):
    LELAKI = "lelaki"
    PEREMPUAN = "perempuan"


class MaritalStatus(str, enum.Enum):
    BUJANG = "bujang"
    DUDA = "duda"
    JANDA = "janda"


class EducationLevel(str, enum.Enum):
    SPM = "spm"
    DIPLOMA = "diploma"
    IJAZAH = "ijazah"
    MASTER = "master"
    PHD = "phd"
    LAIN = "lain"


class IncomeRange(str, enum.Enum):
    BELOW_2K = "below_2k"
    RANGE_2K_5K = "2k_5k"
    RANGE_5K_10K = "5k_10k"
    RANGE_10K_20K = "10k_20k"
    ABOVE_20K = "above_20k"


class MalaysiaState(str, enum.Enum):
    JOHOR = "johor"
    KEDAH = "kedah"
    KELANTAN = "kelantan"
    MELAKA = "melaka"
    NEGERI_SEMBILAN = "negeri_sembilan"
    PAHANG = "pahang"
    PERAK = "perak"
    PERLIS = "perlis"
    PULAU_PINANG = "pulau_pinang"
    SABAH = "sabah"
    SARAWAK = "sarawak"
    SELANGOR = "selangor"
    TERENGGANU = "terengganu"
    WP_KL = "wp_kuala_lumpur"
    WP_PUTRAJAYA = "wp_putrajaya"
    WP_LABUAN = "wp_labuan"


class AccountStatus(str, enum.Enum):
    PENDING_EKYC = "pending_ekyc"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PAUSED = "paused"
    MARRIED = "married"
    DELETED = "deleted"


class SubscriptionTier(str, enum.Enum):
    RAHMAH = "rahmah"
    GOLD = "gold"
    PLATINUM = "platinum"
    PREMIUM = "premium"
    SOVEREIGN = "sovereign"


class PhotoType(str, enum.Enum):
    HEADSHOT = "headshot"
    LIFESTYLE = "lifestyle"


# ─── User Account (Authentication Layer) ───

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Unique code name (e.g. MF41K) — shown instead of real name
    code_name: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    
    # Account state
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus), default=AccountStatus.PENDING_EKYC, nullable=False
    )
    current_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier), default=SubscriptionTier.RAHMAH, nullable=False
    )
    is_verified_t20: Mapped[bool] = mapped_column(Boolean, default=False)
    is_asnaf: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # e-KYC
    ekyc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ekyc_reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    liveness_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    liveness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Profile completion percentage (0-100)
    profile_completion: Mapped[int] = mapped_column(Integer, default=0)
    
    # Device fingerprint hash for anti-fraud
    device_fingerprints: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    
    # Strikes system
    strike_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Wali mode
    wali_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Invisible mode (Sovereign only)
    invisible_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Relationships ──
    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    photos: Mapped[List["UserPhoto"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped[Optional["UserPreference"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    quiz_responses: Mapped[List["QuizResponse"]] = relationship(back_populates="user")
    psychometric_score: Mapped[Optional["PsychometricScore"]] = relationship(
        back_populates="user", uselist=False
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(back_populates="user")
    notifications: Mapped[List["Notification"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("idx_users_status_tier", "status", "current_tier"),
        Index("idx_users_last_active", "last_active_at"),
    )


# ─── User Profile (Personal Details) ───

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    
    # Basic Info
    display_name: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    gender: Mapped[Optional[Gender]] = mapped_column(Enum(Gender), nullable=True)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Physical
    height_cm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Location
    state_of_birth: Mapped[Optional[MalaysiaState]] = mapped_column(
        Enum(MalaysiaState), nullable=True
    )
    state_of_residence: Mapped[Optional[MalaysiaState]] = mapped_column(
        Enum(MalaysiaState), nullable=True
    )
    
    # Education & Career
    education_level: Mapped[Optional[EducationLevel]] = mapped_column(
        Enum(EducationLevel), nullable=True
    )
    occupation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    occupation_category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    income_range: Mapped[Optional[IncomeRange]] = mapped_column(
        Enum(IncomeRange), nullable=True
    )
    
    # Family
    marital_status: Mapped[Optional[MaritalStatus]] = mapped_column(
        Enum(MaritalStatus), nullable=True
    )
    dependants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Bio
    bio_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Selected hobbies (stored as JSON array of hobby IDs)
    hobbies: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    
    # Selected values (from Section 4.1 of blueprint)
    desired_values: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    
    # Red flags / dealbreakers
    red_flags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # ── Relationship ──
    user: Mapped["User"] = relationship(back_populates="profile")

    __table_args__ = (
        CheckConstraint("height_cm IS NULL OR (height_cm >= 140 AND height_cm <= 220)", name="ck_height_range"),
        CheckConstraint("weight_kg IS NULL OR (weight_kg >= 35 AND weight_kg <= 200)", name="ck_weight_range"),
        CheckConstraint("dependants IS NULL OR (dependants >= 0 AND dependants <= 15)", name="ck_dependants_range"),
    )


# ─── User Photos ───

class UserPhoto(Base):
    __tablename__ = "user_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    photo_type: Mapped[PhotoType] = mapped_column(Enum(PhotoType), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # CDN-served URL with dynamic watermark params
    watermarked_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Moderation
    ai_moderation_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    liveness_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="photos")

    __table_args__ = (
        Index("idx_photos_user_type", "user_id", "photo_type"),
    )


# ─── User Preferences (Partner Criteria) ───

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )
    
    # Age range preference
    preferred_age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Location preference (list of acceptable states)
    preferred_states: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    
    # Education preference
    preferred_education_min: Mapped[Optional[EducationLevel]] = mapped_column(
        Enum(EducationLevel), nullable=True
    )
    
    # Income preference
    preferred_income_min: Mapped[Optional[IncomeRange]] = mapped_column(
        Enum(IncomeRange), nullable=True
    )
    
    # Marital status preference
    preferred_marital_status: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    
    # Height preference
    preferred_height_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_height_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="preferences")
