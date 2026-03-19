"""
JODOHKU.MY — Report Service
Real implementation: create and manage user reports
"""
import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Report, ReportCategory, ReportStatus


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_report(
        self,
        reporter_id: UUID,
        reported_user_id: UUID,
        category: str,
        description: str = None,
    ) -> dict:
        try:
            cat = ReportCategory(category)
        except ValueError:
            cat = ReportCategory.OTHER

        report = Report(
            reporter_id=reporter_id,
            reported_user_id=reported_user_id,
            category=cat,
            description=description,
            status=ReportStatus.PENDING,
        )
        self.db.add(report)
        await self.db.flush()

        return {"report_id": report.id, "status": "pending"}
