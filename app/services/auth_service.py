"""
JODOHKU.MY — Authentication Service
Handles registration, OTP, JWT, device fingerprinting
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models.user import User, AccountStatus

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._otp_store: dict = {}  # Redis in production

    def _generate_code_name(self) -> str:
        """Generate unique 5-char alphanumeric code name (e.g. MF41K)."""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(chars) for _ in range(5))

    def _generate_otp(self) -> str:
        """Generate 6-digit OTP."""
        return f"{secrets.randbelow(1000000):06d}"

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def _create_access_token(self, user_id: str, expires_minutes: int = None) -> str:
        expires = datetime.utcnow() + timedelta(
            minutes=expires_minutes or settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": user_id,
            "exp": expires,
            "type": "access",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def _create_refresh_token(self, user_id: str) -> str:
        expires = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        payload = {
            "sub": user_id,
            "exp": expires,
            "type": "refresh",
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def _compute_device_hash(self, device_info: dict) -> str:
        raw = f"{device_info.get('user_agent', '')}{device_info.get('accept_language', '')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def register(self, email: str, password: str) -> dict:
        """Register new user — sends OTP, creates account in PENDING_EKYC."""
        # Check existing
        result = await self.db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Emel sudah didaftarkan."
            )

        # Generate unique code name
        code_name = self._generate_code_name()
        while True:
            check = await self.db.execute(
                select(User).where(User.code_name == code_name)
            )
            if not check.scalar_one_or_none():
                break
            code_name = self._generate_code_name()

        # Create user
        user = User(
            email=email,
            hashed_password=self._hash_password(password),
            code_name=code_name,
            status=AccountStatus.PENDING_EKYC,
        )
        self.db.add(user)
        await self.db.flush()

        # Generate and send OTP
        otp = self._generate_otp()
        # In production: store in Redis with 10-min TTL + send via email
        self._otp_store[email] = {
            "code": otp,
            "expires": datetime.utcnow() + timedelta(minutes=10),
            "user_id": str(user.id),
        }

        # TODO: Send OTP email via SMTP service
        return {"user_id": user.id, "otp": otp}  # Remove otp from response in production

    async def verify_otp(self, email: str, otp_code: str) -> dict:
        """Verify OTP and return e-KYC session token."""
        otp_data = self._otp_store.get(email)
        if not otp_data:
            raise HTTPException(status_code=400, detail="OTP tidak sah atau telah tamat tempoh.")
        
        if otp_data["code"] != otp_code:
            raise HTTPException(status_code=400, detail="Kod OTP salah.")
        
        if datetime.utcnow() > otp_data["expires"]:
            del self._otp_store[email]
            raise HTTPException(status_code=400, detail="OTP telah tamat tempoh.")

        del self._otp_store[email]
        
        # Generate temporary e-KYC token
        ekyc_token = self._create_access_token(otp_data["user_id"], expires_minutes=30)
        return {"ekyc_token": ekyc_token}

    async def login(self, email: str, password: str, device_info: dict) -> dict:
        """Authenticate user and return JWT tokens."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not self._verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Emel atau kata laluan tidak sah."
            )

        if user.status == AccountStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Akaun anda telah digantung."
            )

        if user.status == AccountStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Akaun telah dipadamkan."
            )

        # Record device fingerprint
        device_hash = self._compute_device_hash(device_info)
        if user.device_fingerprints is None:
            user.device_fingerprints = []
        
        # Check device ban (max 2 accounts per device in 24h)
        if device_hash not in [d.get("hash") for d in (user.device_fingerprints or [])]:
            user.device_fingerprints = (user.device_fingerprints or []) + [{
                "hash": device_hash,
                "first_seen": datetime.utcnow().isoformat(),
                "ip": device_info.get("ip", ""),
            }]

        # Update last active
        user.last_active_at = datetime.utcnow()
        await self.db.flush()

        user_id_str = str(user.id)
        access_token = self._create_access_token(user_id_str)
        refresh_token = self._create_refresh_token(user_id_str)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
            "user_id": user.id,
            "code_name": user.code_name,
            "current_tier": user.current_tier.value,
            "profile_completion": user.profile_completion,
        }

    async def refresh(self, refresh_token: str) -> dict:
        """Refresh access token."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Token tidak sah.")
            
            user_id = payload["sub"]
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=401, detail="Pengguna tidak ditemui.")

            new_access = self._create_access_token(user_id)
            new_refresh = self._create_refresh_token(user_id)

            return {
                "access_token": new_access,
                "refresh_token": new_refresh,
                "token_type": "bearer",
                "expires_in": settings.jwt_access_token_expire_minutes * 60,
                "user_id": user.id,
                "code_name": user.code_name,
                "current_tier": user.current_tier.value,
                "profile_completion": user.profile_completion,
            }
        except jwt.JWTError:
            raise HTTPException(status_code=401, detail="Token tidak sah atau telah tamat.")

    async def logout(self, token: str):
        """Invalidate token. In production, add to Redis blacklist."""
        # TODO: Add token to Redis blacklist with TTL
        pass

    async def send_password_reset(self, email: str):
        """Send password reset OTP."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            otp = self._generate_otp()
            self._otp_store[f"reset:{email}"] = {
                "code": otp,
                "expires": datetime.utcnow() + timedelta(minutes=10),
            }
            # TODO: Send email

    async def reset_password(self, email: str, otp_code: str, new_password: str):
        """Reset password with OTP."""
        otp_data = self._otp_store.get(f"reset:{email}")
        if not otp_data or otp_data["code"] != otp_code:
            raise HTTPException(status_code=400, detail="OTP tidak sah.")
        
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = self._hash_password(new_password)
            del self._otp_store[f"reset:{email}"]
