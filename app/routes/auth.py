"""
JODOHKU.MY — Authentication Routes
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    RegisterRequest, OTPVerifyRequest, LoginRequest,
    TokenResponse, RefreshTokenRequest
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    result = await service.register(request.email, request.password)
    return {
        "message": "OTP dihantar ke emel anda. Sah selama 10 minit.",
        "user_id": str(result["user_id"]),
    }


@router.post("/verify-otp")
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify OTP — activates account and returns full JWT tokens.
    Frontend goes directly to app after this step.
    """
    service = AuthService(db)
    result = await service.verify_otp(request.email, request.otp_code)
    return result


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
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
    service = AuthService(db)
    return await service.refresh(request.refresh_token)


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    token = request.headers.get("authorization", "").replace("Bearer ", "")
    await service.logout(token)
    return {"message": "Berjaya log keluar."}


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await request.json()
    email = data.get("email", "")
    service = AuthService(db)
    await service.send_password_reset(email)
    return {"message": "Jika akaun wujud, OTP telah dihantar."}


@router.post("/reset-password")
async def reset_password(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = await request.json()
    email = data.get("email", "")
    otp_code = data.get("otp_code", "")
    new_password = data.get("new_password", "")
    if not email or not otp_code or not new_password:
        raise HTTPException(status_code=400, detail="Sila isi semua medan.")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="Kata laluan minimum 8 aksara.")
    service = AuthService(db)
    await service.reset_password(email, otp_code, new_password)
    return {"message": "Kata laluan berjaya ditukar."}
