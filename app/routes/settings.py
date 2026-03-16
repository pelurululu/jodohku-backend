"""
JODOHKU.MY — Settings Routes
Account management, deletion, pause, report, support
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ReportRequest
from app.services.account_service import AccountService
from app.services.report_service import ReportService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings & Account"])


@router.post("/mark-married")
async def mark_as_married(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark profile as married. Hidden from search within 24 hours."""
    service = AccountService(db)
    await service.mark_married(current_user.id)
    return {"message": "Tahniah! Profil anda akan disembunyikan dalam 24 jam."}


@router.post("/pause")
async def pause_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause account for up to 6 months without deletion."""
    service = AccountService(db)
    await service.pause_account(current_user.id)
    return {"message": "Akaun dijeda selama 6 bulan. Anda boleh kembali bila-bila masa."}


@router.post("/unpause")
async def unpause_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reactivate paused account."""
    service = AccountService(db)
    await service.unpause_account(current_user.id)
    return {"message": "Selamat kembali! Akaun anda telah diaktifkan semula."}


@router.post("/delete-account")
async def request_account_deletion(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Right to Be Forgotten (PDPA compliance).
    
    Protocol:
    - Hard delete: name, email, phone, photos, chat logs from active DB in 72 hours
    - Backup purge within 30 days
    - Financial records kept 7 years (LHDN) but anonymized
    - Deletion certificate sent to user's email
    """
    service = AccountService(db)
    await service.request_deletion(current_user.id)
    return {
        "message": "Permohonan pemadaman diterima. "
                   "Data aktif dipadam dalam 72 jam. "
                   "Sijil pemadaman akan dihantar ke emel anda."
    }


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.change_password(current_user.id, current_password, new_password)
    return {"message": "Kata laluan berjaya ditukar."}


@router.post("/report")
async def report_user(
    request: ReportRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Report a user profile.
    Categories: fake_profile, obscene_content, financial_scam, harassment, other.
    Routed to admin dashboard in real-time.
    """
    service = ReportService(db)
    result = await service.create_report(
        reporter_id=current_user.id,
        reported_user_id=request.reported_user_id,
        category=request.category,
        description=request.description,
    )
    return {
        "message": "Laporan diterima. Pihak pentadbir akan menyemak dalam 24 jam.",
        "report_id": str(result["report_id"]),
    }


@router.post("/block-user/{target_user_id}")
async def block_user(
    target_user_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Block a user. They disappear completely from your view."""
    service = AccountService(db)
    await service.block_user(current_user.id, target_user_id)
    return {"message": "Pengguna telah disekat."}
