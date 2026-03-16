"""
JODOHKU.MY — Matching & Interaction Models
Cosine similarity matching engine data layer
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class MatchStatus(str, enum.Enum):
    SUGGESTED = "suggested"       # Algorithm suggested
    VIEWED = "viewed"             # User viewed the profile
    LIKED = "liked"               # User liked / saved
    LAMAR = "lamar"               # User sent Lamar (initiate chat)
    MUTUAL = "mutual"             # Both users liked each other
    REJECTED = "rejected"         # User dismissed
    BLOCKED = "blocked"           # User blocked


class InteractionType(str, enum.Enum):
    VIEW = "view"
    LIKE = "like"
    LAMAR = "lamar"
    REJECT = "reject"
    BLOCK = "block"
    SAVE_FAVORITE = "save_favorite"
    WHATSAPP_REQUEST = "whatsapp_request"
    WHATSAPP_APPROVED = "whatsapp_approved"
    WHATSAPP_REJECTED = "whatsapp_rejected"


class Match(Base):
    """
    Stores computed match scores between user pairs.
    Only pairs with S(A,B) >= 0.85 are stored.
    """
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    user_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    user_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Cosine similarity score (0.0 to 1.0)
    compatibility_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Score breakdown by component
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    # {
    #   "psychometric": 0.92,
    #   "values_redflags": 0.88,
    #   "demographic": 0.75,
    #   "hobbies": 0.80,
    #   "badges": 0.05
    # }
    
    # Status from user_a's perspective
    status_a: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.SUGGESTED
    )
    # Status from user_b's perspective
    status_b: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), default=MatchStatus.SUGGESTED
    )
    
    # Wingman tip (AI-generated conversation starter)
    wingman_tip_ms: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    wingman_tip_en: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_match_pair"),
        Index("idx_match_user_a", "user_a_id", "compatibility_score"),
        Index("idx_match_user_b", "user_b_id", "compatibility_score"),
        Index("idx_match_score", "compatibility_score"),
    )


class MatchInteraction(Base):
    """Logs every interaction between users for analytics and enforcement."""
    __tablename__ = "match_interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=True
    )
    
    interaction_type: Mapped[InteractionType] = mapped_column(
        Enum(InteractionType), nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_interaction_actor", "actor_id", "created_at"),
        Index("idx_interaction_target", "target_id"),
    )


class Favorite(Base):
    """User's saved/favorited profiles."""
    __tablename__ = "favorites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "target_id", name="uq_favorite_pair"),
    )
