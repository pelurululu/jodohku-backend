"""
JODOHKU.MY — Profile Routes
Profile CRUD, photo upload, preferences, completion tracking
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    ProfileUpdateRequest, ProfileResponse, PhotoResponse,
    PreferenceUpdateRequest
)
from app.services.profile_service import ProfileService
from app.services.photo_service import PhotoService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's full profile."""
    service = ProfileService(db)
    return await service.get_profile(current_user.id, viewer_id=current_user.id)


@router.put("/me")
async def update_my_profile(
    request: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update profile fields.
    Recalculates profile_completion percentage after each update.
    Triggers matching engine recalculation if significant fields change.
    """
    service = ProfileService(db)
    result = await service.update_profile(current_user.id, request)
    return {
        "message": "Profil dikemaskini.",
        "profile_completion": result["profile_completion"],
        "newly_unlocked": result.get("newly_unlocked", []),
    }


@router.get("/{code_name}", response_model=ProfileResponse)
async def get_profile_by_code(
    code_name: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    View another user's profile.
    - Photos blurred if viewer is Rahmah tier
    - Records view interaction
    - Checks invisible mode
    """
    service = ProfileService(db)
    profile = await service.get_profile_by_code(
        code_name, viewer_id=current_user.id, viewer_tier=current_user.current_tier
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profil tidak ditemui.")
    return profile


# ─── Photo Management ───

@router.post("/photos/upload")
async def upload_photo(
    photo_type: str,  # "headshot" or "lifestyle"
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload profile photo.
    - Min 500x500px for headshot
    - AI moderation check before approval
    - Liveness match against e-KYC selfie
    """
    service = PhotoService(db)
    result = await service.upload_photo(current_user.id, photo_type, file)
    return {
        "message": "Gambar dimuat naik. Menunggu pengesahan.",
        "photo_id": str(result["photo_id"]),
        "status": result["moderation_status"],
    }


@router.delete("/photos/{photo_id}")
async def delete_photo(
    photo_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a profile photo."""
    service = PhotoService(db)
    await service.delete_photo(current_user.id, photo_id)
    return {"message": "Gambar dipadamkan."}


@router.put("/photos/{photo_id}/reorder")
async def reorder_photo(
    photo_id: UUID,
    new_order: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change photo display order."""
    service = PhotoService(db)
    await service.reorder(current_user.id, photo_id, new_order)
    return {"message": "Susunan dikemaskini."}


# ─── Preferences ───

@router.get("/me/preferences")
async def get_preferences(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's partner preferences."""
    service = ProfileService(db)
    return await service.get_preferences(current_user.id)


@router.put("/me/preferences")
async def update_preferences(
    request: PreferenceUpdateRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update partner preference filters."""
    service = ProfileService(db)
    await service.update_preferences(current_user.id, request)
    return {"message": "Keutamaan carian dikemaskini."}


# ─── Profile Completion Status ───

@router.get("/me/completion")
async def get_completion_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed breakdown of profile completion.
    Used for progress bar and motivational prompts.
    """
    service = ProfileService(db)
    return await service.get_completion_breakdown(current_user.id)


# ─── Verified T20 Badge Application ───

@router.post("/verify-t20")
async def apply_t20_verification(
    file: UploadFile = File(...),
    doc_type: str = "ea_form",  # "ea_form" or "bank_statement"
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload financial document for T20 badge verification.
    Documents reviewed manually within 48 hours.
    Documents deleted from server after approval.
    """
    service = ProfileService(db)
    result = await service.submit_t20_verification(current_user.id, file, doc_type)
    return {
        "message": "Dokumen dihantar untuk semakan. Keputusan dalam 48 jam.",
        "application_id": str(result["application_id"]),
    }
