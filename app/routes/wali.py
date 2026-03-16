"""
JODOHKU.MY — Wali/Mahram Mode Routes
Guardian read-only access to matchmaking process
"""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import WaliInviteRequest
from app.services.wali_service import WaliService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/wali", tags=["Wali/Mahram Mode"])


@router.post("/invite")
async def invite_wali(
    request: WaliInviteRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Invite wali/mahram via email.
    Creates read-only observer account.
    Only available for female users.
    """
    service = WaliService(db)
    result = await service.send_invitation(
        user_id=current_user.id,
        wali_email=request.wali_email,
        wali_name=request.wali_name,
        relation=request.relation,
    )
    return {
        "message": "Jemputan dihantar kepada wali.",
        "invitation_id": str(result["invitation_id"]),
    }


@router.get("/status")
async def get_wali_status(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current wali mode status and active wali accounts."""
    service = WaliService(db)
    return await service.get_status(current_user.id)


@router.post("/toggle")
async def toggle_wali_mode(
    enabled: bool,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable wali mode."""
    service = WaliService(db)
    await service.toggle_mode(current_user.id, enabled)
    status_text = "diaktifkan" if enabled else "dinyahaktifkan"
    return {"message": f"Mod wali {status_text}."}


@router.delete("/revoke/{invitation_id}")
async def revoke_wali_access(
    invitation_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a wali's access."""
    service = WaliService(db)
    await service.revoke_access(current_user.id, invitation_id)
    return {"message": "Akses wali telah dibatalkan."}


# ─── Wali Login (separate auth flow) ───

@router.post("/login")
async def wali_login(
    email: str,
    password: str,
    token: str,  # Invitation token
    db: AsyncSession = Depends(get_db),
):
    """
    Wali login with invitation token.
    Returns read-only session token.
    """
    service = WaliService(db)
    return await service.wali_login(email, password, token)


@router.get("/dashboard")
async def wali_dashboard(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Wali read-only dashboard.
    Shows: all proposals received, all active conversations, profile views.
    """
    service = WaliService(db)
    return await service.get_wali_dashboard(current_user.id)
