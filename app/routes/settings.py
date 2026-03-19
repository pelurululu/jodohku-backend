"""
JODOHKU.MY — Settings Routes
Fixed: DELETE /delete, PUT /password, JSON body for change_password
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ReportRequest
from app.services.account_service import AccountService
from app.services.report_service import ReportService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["Settings & Account"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class DeleteAccountRequest(BaseModel):
    reason: Optional[str] = ""


# ── PUT /password — frontend calls this ──
@router.put("/password")
@router.post("/change-password")  # keep old for compatibility
async def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    return await service.change_password(
        current_user.id, request.current_password, request.new_password
    )


@router.post("/pause")
async def pause_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    return await service.pause_account(current_user.id)


@router.post("/unpause")
async def unpause_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    return await service.unpause_account(current_user.id)


# ── DELETE /delete — frontend calls this ──
@router.delete("/delete")
@router.post("/delete-account")  # keep old for compatibility
async def delete_account(
    request: DeleteAccountRequest = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    return await service.request_deletion(current_user.id)


@router.post("/mark-married")
async def mark_as_married(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    return await service.mark_married(current_user.id)


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


@router.post("/block-user/{target_user_id}")
async def block_user(
    target_user_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    return await service.block_user(current_user.id, target_user_id)
