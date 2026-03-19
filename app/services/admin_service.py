"""
JODOHKU.MY — Admin Service
Graceful stub — returns empty responses instead of crashing.
Full implementation pending.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_metrics(self) -> dict:
        return {
            "mau": 0, "dau": 0, "arpu": 0.0, "churn_rate": 0.0,
            "ltv": 0.0, "cac": 0.0, "ltv_cac_ratio": 0.0,
            "conversion_rate": 0.0, "match_rate": 0.0,
            "gender_ratio": {"male": 0, "female": 0},
            "revenue_today": 0.0, "revenue_month": 0.0,
            "active_subscriptions": {}, "pending_reports": 0,
            "pending_asnaf": 0, "pending_t20": 0,
        }

    async def get_revenue_report(self, period: str) -> dict:
        return {"period": period, "revenue": 0.0, "transactions": []}

    async def list_users(self, search, status, tier, page) -> dict:
        return {"users": [], "total": 0, "page": page}

    async def suspend_user(self, user_id: UUID, reason: str, duration_hours: int, admin_id: UUID):
        from app.models.user import User, AccountStatus
        user = await self.db.get(User, user_id)
        if user:
            user.status = AccountStatus.SUSPENDED
            await self.db.flush()

    async def kill_switch(self, user_id: UUID, reason: str, admin_id: UUID):
        from app.models.user import User, AccountStatus
        user = await self.db.get(User, user_id)
        if user:
            user.status = AccountStatus.SUSPENDED
            await self.db.flush()

    async def list_reports(self, status, category, page) -> dict:
        return {"reports": [], "total": 0, "page": page}

    async def resolve_report(self, report_id: UUID, resolution: str, admin_notes: str, admin_id: UUID):
        from app.models.admin import Report, ReportStatus
        from sqlalchemy import select
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        report = result.scalar_one_or_none()
        if report:
            report.status = ReportStatus.RESOLVED
            report.admin_notes = admin_notes
            report.resolved_at = __import__('datetime').datetime.utcnow()
            await self.db.flush()

    async def get_report_chat_log(self, report_id: UUID) -> dict:
        return {"messages": []}

    async def list_pending_asnaf(self) -> dict:
        return {"applications": []}

    async def approve_asnaf(self, application_id: UUID, admin_notes: str, admin_id: UUID):
        pass

    async def reject_asnaf(self, application_id: UUID, admin_notes: str, admin_id: UUID):
        pass

    async def list_pending_t20(self) -> dict:
        return {"applications": []}

    async def approve_t20(self, user_id: UUID, admin_id: UUID):
        from app.models.user import User
        user = await self.db.get(User, user_id)
        if user:
            user.is_verified_t20 = True
            await self.db.flush()

    async def list_transactions(self, gateway, status, page) -> dict:
        return {"transactions": [], "total": 0, "page": page}

    async def get_active_subscriptions_by_tier(self) -> dict:
        return {"rahmah": 0, "gold": 0, "platinum": 0, "premium": 0, "sovereign": 0}

    async def trace_watermark(self, image_hash: str) -> dict:
        return {"found": False, "image_hash": image_hash}

    async def get_audit_log(self, page: int) -> dict:
        return {"logs": [], "total": 0, "page": page}
