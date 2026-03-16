"""
JODOHKU.MY — Admin Routes (God Mode)
Full admin dashboard with all management capabilities
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import AdminDashboardMetrics
from app.services.admin_service import AdminService
from app.middleware.auth import get_admin_user

router = APIRouter(prefix="/admin", tags=["Admin God Mode"])


# ─── Dashboard ───

@router.get("/dashboard", response_model=AdminDashboardMetrics)
async def get_dashboard(
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """CEO dashboard with all business metrics."""
    service = AdminService(db)
    return await service.get_dashboard_metrics()


@router.get("/dashboard/revenue")
async def get_revenue_report(
    period: str = "monthly",  # daily, monthly, yearly
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_revenue_report(period)


# ─── User Management ───

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    page: int = Query(1, ge=1),
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_users(search, status, tier, page)


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: UUID,
    reason: str,
    duration_hours: int = 48,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Suspend a user account."""
    service = AdminService(db)
    await service.suspend_user(user_id, reason, duration_hours, admin.id)
    return {"message": "Akaun digantung."}


@router.post("/users/{user_id}/kill-switch")
async def kill_switch(
    user_id: UUID,
    reason: str,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Immediately deactivate scammer profile."""
    service = AdminService(db)
    await service.kill_switch(user_id, reason, admin.id)
    return {"message": "Profil dimatikan serta-merta."}


# ─── Reports & Tribunal ───

@router.get("/reports")
async def list_reports(
    status: Optional[str] = None,
    category: Optional[str] = None,
    page: int = Query(1, ge=1),
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_reports(status, category, page)


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: UUID,
    resolution: str,
    admin_notes: str,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    await service.resolve_report(report_id, resolution, admin_notes, admin.id)
    return {"message": "Laporan diselesaikan."}


@router.get("/reports/{report_id}/chat-log")
async def get_report_chat_log(
    report_id: UUID,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Review chat logs for a reported conversation."""
    service = AdminService(db)
    return await service.get_report_chat_log(report_id)


# ─── Asnaf Management ───

@router.get("/asnaf/pending")
async def list_pending_asnaf(
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_pending_asnaf()


@router.post("/asnaf/{application_id}/approve")
async def approve_asnaf(
    application_id: UUID,
    admin_notes: Optional[str] = None,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    await service.approve_asnaf(application_id, admin_notes, admin.id)
    return {"message": "Permohonan Asnaf diluluskan."}


@router.post("/asnaf/{application_id}/reject")
async def reject_asnaf(
    application_id: UUID,
    admin_notes: str,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    await service.reject_asnaf(application_id, admin_notes, admin.id)
    return {"message": "Permohonan Asnaf ditolak."}


# ─── T20 Verification ───

@router.get("/t20/pending")
async def list_pending_t20(
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_pending_t20()


@router.post("/t20/{user_id}/approve")
async def approve_t20(
    user_id: UUID,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    await service.approve_t20(user_id, admin.id)
    return {"message": "Lencana Verified T20 diberikan."}


# ─── Financial Monitoring ───

@router.get("/transactions")
async def list_all_transactions(
    gateway: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.list_transactions(gateway, status, page)


@router.get("/subscriptions/active")
async def active_subscriptions_by_tier(
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_active_subscriptions_by_tier()


# ─── Watermark Forensics ───

@router.get("/watermark/trace/{image_hash}")
async def trace_watermark(
    image_hash: str,
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Trace leaked image back to viewer using watermark data."""
    service = AdminService(db)
    return await service.trace_watermark(image_hash)


# ─── Audit Trail ───

@router.get("/audit-log")
async def get_audit_log(
    page: int = Query(1, ge=1),
    admin=Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    service = AdminService(db)
    return await service.get_audit_log(page)
