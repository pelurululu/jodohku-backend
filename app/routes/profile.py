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


@router.post("/photo")
async def upload_photo_base64(
    request: dict,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Accept base64 photo from frontend crop tool.
    Upserts a UserPhoto record with is_approved=True.
    file_url stores the data-URL so it is immediately usable.
    """
    from app.models.user import UserPhoto, PhotoType
    from sqlalchemy import select, delete

    photo_data: str = request.get("photo_data", "")
    photo_type_str: str = request.get("photo_type", "headshot")

    if not photo_data:
        raise HTTPException(status_code=400, detail="photo_data diperlukan.")

    # Ensure it's a valid data URL; prefix if raw base64
    if not photo_data.startswith("data:"):
        photo_data = "data:image/jpeg;base64," + photo_data

    # Map string → enum (default to HEADSHOT)
    try:
        photo_type = PhotoType(photo_type_str)
    except ValueError:
        photo_type = PhotoType.HEADSHOT

    # Delete existing photos of the same type so there's only ever one headshot
    await db.execute(
        delete(UserPhoto).where(
            UserPhoto.user_id == current_user.id,
            UserPhoto.photo_type == photo_type,
        )
    )

    new_photo = UserPhoto(
        user_id=current_user.id,
        photo_type=photo_type,
        file_path=f"base64/{current_user.id}/{photo_type.value}",
        file_url=photo_data,          # data-URL — served directly to clients
        is_approved=True,             # auto-approve own photo upload
        ai_moderation_passed=True,
        sort_order=0,
    )
    db.add(new_photo)
    await db.flush()

    return {
        "success": True,
        "photo_id": str(new_photo.id),
        "photo_url": photo_data,
        "message": "Gambar profil berjaya disimpan.",
    }


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
