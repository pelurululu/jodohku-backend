"""
JODOHKU.MY — Database Models
All SQLAlchemy models consolidated here for Alembic discovery
"""

from app.models.user import User, UserProfile, UserPhoto, UserPreference
from app.models.quiz import QuizQuestion, QuizResponse, PsychometricScore
from app.models.matching import Match, MatchInteraction, Favorite
from app.models.chat import Conversation, Message, IceBreaker
from app.models.subscription import Subscription, Transaction, GoldenTicket
from app.models.admin import AdminUser, Report, StrikeRecord, AuditLog
from app.models.wali import WaliInvitation, WaliAccess
from app.models.notification import Notification, NotificationPreference
from app.models.asnaf import AsnafApplication, AsnafVerification

__all__ = [
    "User", "UserProfile", "UserPhoto", "UserPreference",
    "QuizQuestion", "QuizResponse", "PsychometricScore",
    "Match", "MatchInteraction", "Favorite",
    "Conversation", "Message", "IceBreaker",
    "Subscription", "Transaction", "GoldenTicket",
    "AdminUser", "Report", "StrikeRecord", "AuditLog",
    "WaliInvitation", "WaliAccess",
    "Notification", "NotificationPreference",
    "AsnafApplication", "AsnafVerification",
]
