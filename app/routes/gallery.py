"""
JODOHKU.MY — Gallery & Matching Routes
Bilik Pameran with cosine similarity matching engine
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    GalleryResponse, GalleryFilters, MatchActionRequest, ProfileResponse
)
from app.services.matching_service import MatchingService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/gallery", tags=["Bilik Pameran & Matching"])


@router.get("/", response_model=GalleryResponse)
async def get_gallery(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    states: Optional[str] = None,
    education_min: Optional[str] = None,
    income_min: Optional[str] = None,
    marital_status: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Bilik Pameran — vertical scroll gallery.
    
    Only profiles with S(A,B) >= 0.85 compatibility are shown.
    Results sorted by: tier priority > compatibility score > last active.
    
    Tier-based limits:
    - Rahmah: 10 views/day
    - Gold: 30 views/day
    - Platinum+: Unlimited
    
    Photos blurred for Rahmah tier viewers.
    Invisible mode users (Sovereign) excluded from results.
    """
    filters = GalleryFilters(
        age_min=age_min,
        age_max=age_max,
        states=states.split(",") if states else None,
        education_min=education_min,
        income_min=income_min,
        marital_status=marital_status.split(",") if marital_status else None,
    )
    
    service = MatchingService(db)
    return await service.get_gallery(
        user_id=current_user.id,
        tier=current_user.current_tier,
        filters=filters,
        page=page,
        page_size=page_size,
    )


@router.post("/action")
async def perform_match_action(
    request: MatchActionRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform action on a profile:
    - "like": Save to liked list
    - "reject": Dismiss from gallery
    - "block": Permanently block user
    - "save_favorite": Add to favorites
    - "lamar": Initiate chat (sends to chat system)
    
    'Lamar' action requires at least 1 ice-breaker or custom message.
    """
    service = MatchingService(db)
    result = await service.perform_action(
        actor_id=current_user.id,
        target_id=request.target_user_id,
        action=request.action,
        actor_tier=current_user.current_tier,
    )
    return result


@router.get("/favorites")
async def get_favorites(
    page: int = Query(1, ge=1),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's saved/favorited profiles."""
    service = MatchingService(db)
    return await service.get_favorites(current_user.id, page)


@router.get("/who-liked-me")
async def who_liked_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    See who liked your profile.
    Gold+ tier: see full profiles.
    Rahmah: see count only.
    """
    service = MatchingService(db)
    return await service.get_who_liked_me(
        current_user.id, current_user.current_tier
    )


@router.get("/compatibility/{target_code_name}")
async def get_compatibility_report(
    target_code_name: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed compatibility breakdown between two users.
    Shows score per component: psychometric, values, demographic, hobbies.
    """
    service = MatchingService(db)
    return await service.get_compatibility_report(
        current_user.id, target_code_name
    )
