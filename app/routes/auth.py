"""
JODOHKU.MY — Authentication Routes
Registration, OTP, Login, Token Refresh, e-KYC
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    RegisterRequest, OTPVerifyRequest, LoginRequest,
    TokenResponse, RefreshTokenRequest
)
from app.services.auth_service import AuthService
from app.services.ekyc_service import EKYCService
from app.middleware.rate_limiter import rate_limit

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 1: Register with email.
    - Creates account in PENDING_EKYC status
    - Sends 6-digit OTP to email (valid 10 minutes)
    - Generates unique code name (e.g. MF41K)
    """
    service = AuthService(db)
    result = await service.register(request.email, request.password)
    return {
        "message": "OTP dihantar ke emel anda. Sah selama 10 minit.",
        "message_en": "OTP sent to your email. Valid for 10 minutes.",
        "user_id": str(result["user_id"]),
    }


@router.post("/verify-otp")
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 2: Verify OTP code from email.
    Returns temporary token for e-KYC step.
    """
    service = AuthService(db)
    result = await service.verify_otp(request.email, request.otp_code)
    return {
        "message": "OTP disahkan. Sila teruskan ke pengesahan e-KYC.",
        "ekyc_token": result["ekyc_token"],
    }


@router.post("/ekyc/initiate")
async def initiate_ekyc(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Step 3: Initiate e-KYC verification.
    - Returns session URL for Jumio/MyTunai widget
    - User uploads MyKad photo + live selfie
    """
    ekyc_service = EKYCService(db)
    session = await ekyc_service.create_verification_session(request)
    return {
        "verification_url": session["url"],
        "session_id": session["session_id"],
        "expires_in": 1800,  # 30 minutes
    }


@router.post("/ekyc/callback")
async def ekyc_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    e-KYC webhook callback from Jumio/MyTunai.
    Activates account if verification passes (≥90% match).
    """
    ekyc_service = EKYCService(db)
    body = await request.json()
    result = await ekyc_service.process_callback(body)
    return {"status": result["status"]}


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email + password.
    Returns JWT access token + refresh token.
    Records device fingerprint for anti-fraud.
    """
    service = AuthService(db)
    
    # Extract device fingerprint from headers
    device_info = {
        "user_agent": req.headers.get("user-agent", ""),
        "accept_language": req.headers.get("accept-language", ""),
        "ip": req.client.host if req.client else "unknown",
    }
    
    result = await service.login(request.email, request.password, device_info)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh expired access token using refresh token."""
    service = AuthService(db)
    result = await service.refresh(request.refresh_token)
    return result


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Invalidate current session tokens."""
    service = AuthService(db)
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    await service.logout(token)
    return {"message": "Berjaya log keluar."}


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """Send password reset OTP to email."""
    service = AuthService(db)
    await service.send_password_reset(email)
    return {"message": "Jika akaun wujud, OTP telah dihantar."}


@router.post("/reset-password")
async def reset_password(
    email: str,
    otp_code: str,
    new_password: str,
    db: AsyncSession = Depends(get_db),
):
    """Reset password with OTP verification."""
    service = AuthService(db)
    await service.reset_password(email, otp_code, new_password)
    return {"message": "Kata laluan berjaya ditukar."}
