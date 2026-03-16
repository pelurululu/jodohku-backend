"""
JODOHKU.MY — Pydantic Schemas
Request/Response validation for all API endpoints
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ═══════════════════════════════════════════
#  AUTH SCHEMAS
# ═══════════════════════════════════════════

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Mesti ada huruf besar")
        if not any(c.isdigit() for c in v):
            raise ValueError("Mesti ada nombor")
        return v


class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: UUID
    code_name: str
    current_tier: str
    profile_completion: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# ═══════════════════════════════════════════
#  USER PROFILE SCHEMAS
# ═══════════════════════════════════════════

class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=16)
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
    height_cm: Optional[int] = Field(None, ge=140, le=220)
    weight_kg: Optional[int] = Field(None, ge=35, le=200)
    state_of_birth: Optional[str] = None
    state_of_residence: Optional[str] = None
    education_level: Optional[str] = None
    occupation: Optional[str] = Field(None, max_length=50)
    occupation_category: Optional[str] = None
    income_range: Optional[str] = None
    marital_status: Optional[str] = None
    dependants: Optional[int] = Field(None, ge=0, le=15)
    bio_text: Optional[str] = Field(None, max_length=500)
    hobbies: Optional[List[str]] = None
    desired_values: Optional[List[str]] = Field(None, min_length=5, max_length=10)
    red_flags: Optional[List[str]] = None


class ProfileResponse(BaseModel):
    user_id: UUID
    code_name: str
    display_name: Optional[str]
    gender: Optional[str]
    age: Optional[int]
    height_cm: Optional[int]
    weight_kg: Optional[int]
    state_of_residence: Optional[str]
    education_level: Optional[str]
    occupation: Optional[str]
    income_range: Optional[str]
    marital_status: Optional[str]
    dependants: Optional[int]
    bio_text: Optional[str]
    hobbies: List[str]
    photos: List["PhotoResponse"]
    current_tier: str
    is_verified_t20: bool
    profile_completion: int
    compatibility_score: Optional[float] = None
    wingman_tip: Optional[str] = None
    is_online: bool = False
    last_active: Optional[str] = None

    class Config:
        from_attributes = True


class PhotoResponse(BaseModel):
    id: UUID
    photo_type: str
    url: str
    is_blurred: bool = False


class PreferenceUpdateRequest(BaseModel):
    preferred_age_min: Optional[int] = Field(None, ge=22, le=55)
    preferred_age_max: Optional[int] = Field(None, ge=22, le=55)
    preferred_states: Optional[List[str]] = None
    preferred_education_min: Optional[str] = None
    preferred_income_min: Optional[str] = None
    preferred_marital_status: Optional[List[str]] = None
    preferred_height_min: Optional[int] = None
    preferred_height_max: Optional[int] = None


# ═══════════════════════════════════════════
#  QUIZ SCHEMAS
# ═══════════════════════════════════════════

class QuizQuestionResponse(BaseModel):
    id: UUID
    domain: str
    text_ms: str
    text_en: str
    sequence_number: int
    is_core: bool


class QuizAnswerRequest(BaseModel):
    question_id: UUID
    score: int = Field(ge=1, le=5)
    time_taken_seconds: Optional[int] = None


class QuizBatchAnswerRequest(BaseModel):
    answers: List[QuizAnswerRequest]


class PsychometricScoreResponse(BaseModel):
    domains: dict  # { "communication": 0.85, "empathy": 0.72, ... }
    questions_answered: int
    confidence: float


# ═══════════════════════════════════════════
#  GALLERY / MATCHING SCHEMAS
# ═══════════════════════════════════════════

class GalleryFilters(BaseModel):
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    states: Optional[List[str]] = None
    education_min: Optional[str] = None
    income_min: Optional[str] = None
    marital_status: Optional[List[str]] = None


class GalleryResponse(BaseModel):
    profiles: List[ProfileResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool


class MatchActionRequest(BaseModel):
    target_user_id: UUID
    action: str  # "like" | "reject" | "block" | "save_favorite" | "lamar"


# ═══════════════════════════════════════════
#  CHAT SCHEMAS
# ═══════════════════════════════════════════

class ConversationResponse(BaseModel):
    id: UUID
    partner_code_name: str
    partner_photo_url: Optional[str]
    partner_tier: str
    status: str
    last_message: Optional[str]
    last_message_at: Optional[datetime]
    unread_count: int
    is_online: bool
    compatibility_score: Optional[float]


class MessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    is_ice_breaker: bool = False


class MessageResponse(BaseModel):
    id: UUID
    sender_code_name: str
    content: str
    status: str
    is_ice_breaker: bool
    created_at: datetime


class WhatsAppRequestAction(BaseModel):
    conversation_id: UUID
    action: str  # "request" | "approve" | "reject"


# ═══════════════════════════════════════════
#  PAYMENT / SUBSCRIPTION SCHEMAS
# ═══════════════════════════════════════════

class SubscriptionPlanResponse(BaseModel):
    tier: str
    price_myr: float
    duration_days: int
    features: dict
    badge_label: str
    badge_color: str


class CreatePaymentRequest(BaseModel):
    tier: str
    promo_code: Optional[str] = None


class PaymentCallbackData(BaseModel):
    bill_code: str
    status: str
    transaction_id: str
    gateway: str


class SubscriptionResponse(BaseModel):
    tier: str
    starts_at: datetime
    expires_at: datetime
    grace_period_ends_at: Optional[datetime]
    is_active: bool
    refund_eligible: bool
    days_remaining: int


class RefundRequest(BaseModel):
    reason: Optional[str] = None


# ═══════════════════════════════════════════
#  NOTIFICATION SCHEMAS
# ═══════════════════════════════════════════

class NotificationResponse(BaseModel):
    id: UUID
    type: str
    title: str
    body: str
    action_url: Optional[str]
    is_read: bool
    created_at: datetime


# ═══════════════════════════════════════════
#  WALI MODE SCHEMAS
# ═══════════════════════════════════════════

class WaliInviteRequest(BaseModel):
    wali_email: EmailStr
    wali_name: str = Field(max_length=100)
    relation: str  # father, brother, uncle, etc.


# ═══════════════════════════════════════════
#  REPORT SCHEMAS
# ═══════════════════════════════════════════

class ReportRequest(BaseModel):
    reported_user_id: UUID
    category: str  # fake_profile, obscene_content, financial_scam, harassment, other
    description: Optional[str] = Field(None, max_length=1000)


# ═══════════════════════════════════════════
#  ADMIN SCHEMAS
# ═══════════════════════════════════════════

class AdminDashboardMetrics(BaseModel):
    mau: int
    dau: int
    arpu: float
    churn_rate: float
    ltv: float
    cac: float
    ltv_cac_ratio: float
    conversion_rate: float
    match_rate: float
    gender_ratio: dict
    revenue_today: float
    revenue_month: float
    active_subscriptions: dict  # { "gold": 120, "platinum": 45, ... }
    pending_reports: int
    pending_asnaf: int
    pending_t20: int
