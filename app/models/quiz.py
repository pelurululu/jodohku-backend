"""
JODOHKU.MY — Psychometric Quiz Models
30-question quiz engine with adaptive branching logic
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, Enum, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.database import Base


class QuizDomain(str, enum.Enum):
    STRESS_MANAGEMENT = "stress_management"
    COMMUNICATION = "communication"
    EMPATHY = "empathy"
    FUTURE_PLANNING = "future_planning"
    ACCEPTING_CRITICISM = "accepting_criticism"
    DISCIPLINE = "discipline"
    FINANCIAL_MANAGEMENT = "financial_management"
    SPIRITUALITY = "spirituality"
    COOPERATION = "cooperation"
    FORGIVENESS = "forgiveness"
    RESILIENCE = "resilience"
    LEADERSHIP = "leadership"


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    domain: Mapped[QuizDomain] = mapped_column(Enum(QuizDomain), nullable=False)
    text_ms: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str] = mapped_column(Text, nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    branching_logic: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_core: Mapped[bool] = mapped_column(Boolean, default=False)
    is_reverse_scored: Mapped[bool] = mapped_column(Boolean, default=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_quiz_domain_seq", "domain", "sequence_number"),
    )


class QuizResponse(Base):
    __tablename__ = "quiz_responses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quiz_questions.id"),
        nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="quiz_responses")

    __table_args__ = (
        Index("idx_quiz_resp_user", "user_id"),
        Index("idx_quiz_resp_question", "question_id"),
    )


class PsychometricScore(Base):
    """
    Computed vector for each user.
    Uses domain_scores JSONB for flexibility — quiz_service writes dict here.
    Individual domain columns kept for direct SQL queries.
    """
    __tablename__ = "psychometric_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )

    # ── Individual domain scores (0.0 to 1.0) ──
    stress_management: Mapped[float] = mapped_column(Float, default=0.0)
    communication: Mapped[float] = mapped_column(Float, default=0.0)
    empathy: Mapped[float] = mapped_column(Float, default=0.0)
    future_planning: Mapped[float] = mapped_column(Float, default=0.0)
    accepting_criticism: Mapped[float] = mapped_column(Float, default=0.0)
    discipline: Mapped[float] = mapped_column(Float, default=0.0)
    financial_management: Mapped[float] = mapped_column(Float, default=0.0)
    spirituality: Mapped[float] = mapped_column(Float, default=0.0)
    cooperation: Mapped[float] = mapped_column(Float, default=0.0)
    forgiveness: Mapped[float] = mapped_column(Float, default=0.0)
    resilience: Mapped[float] = mapped_column(Float, default=0.0)
    leadership: Mapped[float] = mapped_column(Float, default=0.0)

    # ── JSONB dict — used by quiz_service ──
    # { "communication": 0.85, "empathy": 0.72, ... }
    domain_scores: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # ── Full vector for cosine similarity ──
    vector: Mapped[list] = mapped_column(JSONB, default=list)

    questions_answered: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"] = relationship(back_populates="psychometric_score")
