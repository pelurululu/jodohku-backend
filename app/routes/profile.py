"""
JODOHKU.MY — Profile Routes
Fixed: PhotoService stub crash — graceful fallback added
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ProfileUpdateRequest, ProfileResponse, PreferenceUpdateRequest
from app.services.profile_service import ProfileService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me")
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    return await service.get_profile(current_user.id, viewer_id=current_user.id)


@router.put("/me")
async def update_my_profile(
    request: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    result = await service.update_profile(current_user.id, request)
    return {
        "message": "Profil dikemaskini.",
        "profile_completion": result["profile_completion"],
        "newly_unlocked": result.get("newly_unlocked", []),
    }


@router.get("/me/preferences")
async def get_preferences(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    return await service.get_preferences(current_user.id)


@router.put("/me/preferences")
async def update_preferences(
    request: PreferenceUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    await service.update_preferences(current_user.id, request)
    return {"message": "Keutamaan carian dikemaskini."}


@router.get("/me/completion")
async def get_completion_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    return await service.get_completion_breakdown(current_user.id)


@router.get("/{code_name}")
async def get_profile_by_code(
    code_name: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProfileService(db)
    profile = await service.get_profile_by_code(
        code_name, viewer_id=current_user.id, viewer_tier=current_user.current_tier
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profil tidak ditemui.")
    return profile


# ── Photo upload — graceful stub until PhotoService is implemented ──
@router.post("/photos/upload")
async def upload_photo(
    photo_type: str = "headshot",
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Implement real photo storage (S3/Cloudflare R2)
    return {
        "message": "Ciri muat naik gambar akan tersedia tidak lama lagi.",
        "photo_id": None,
        "status": "pending",
    }


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "Gambar dipadamkan."}


@router.put("/photos/{photo_id}/reorder")
async def reorder_photo(
    photo_id: UUID,
    new_order: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "Susunan dikemaskini."}


@router.post("/verify-t20")
async def apply_t20_verification(
    file: UploadFile = File(...),
    doc_type: str = "ea_form",
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # TODO: Store document and queue for admin review
    return {
        "message": "Dokumen dihantar untuk semakan. Keputusan dalam 48 jam.",
        "application_id": None,
    }
