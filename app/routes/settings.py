"""
JODOHKU.MY — Settings Routes
Fixed to match frontend API calls
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ReportRequest
from app.services.account_service import AccountService
from app.services.report_service import ReportService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings & Account"])


# ── Request schemas ──
class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class DeleteRequest(BaseModel):
    reason: str = ""

class PauseRequest(BaseModel):
    pass


# ── Password ──
@router.put("/password")
@router.post("/change-password")  # keep old route too
async def change_password(
    request: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.change_password(
        current_user.id,
        request.current_password,
        request.new_password
    )
    return {"message": "Kata laluan berjaya ditukar."}


# ── Pause ──
@router.post("/pause")
async def pause_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.pause_account(current_user.id)
    return {"message": "Akaun dijeda. Anda boleh kembali bila-bila masa."}


@router.post("/unpause")
async def unpause_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.unpause_account(current_user.id)
    return {"message": "Selamat kembali! Akaun anda telah diaktifkan semula."}


# ── Delete ──
@router.delete("/delete")
@router.post("/delete-account")  # keep old route too
async def delete_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.request_deletion(current_user.id)
    return {
        "message": "Permohonan pemadaman diterima. "
                   "Data aktif dipadam dalam 72 jam. "
                   "Sijil pemadaman akan dihantar ke emel anda."
    }


# ── Mark married ──
@router.post("/mark-married")
async def mark_as_married(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.mark_married(current_user.id)
    return {"message": "Tahniah! Profil anda akan disembunyikan dalam 24 jam."}


# ── Report ──
@router.post("/report")
async def report_user(
    request: ReportRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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


# ── Block ──
@router.post("/block-user/{target_user_id}")
async def block_user(
    target_user_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    await service.block_user(current_user.id, target_user_id)
    return {"message": "Pengguna telah disekat."}
