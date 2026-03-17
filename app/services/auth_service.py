"""
JODOHKU.MY — Authentication Service
OTP stored in Redis (not memory) to survive restarts
Email via Brevo API
"""

import secrets
import hashlib
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt
from passlib.context import CryptContext
import redis.asyncio as aioredis

from app.config import get_settings
from app.models.user import User, AccountStatus

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_redis():
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )


async def send_otp_email(email: str, otp: str):
    html = f"""<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#FAFAF8;border-radius:16px">
<h2 style="color:#1B2A4A;text-align:center">Jodohku<span style="color:#C8A23C">.my</span></h2>
<div style="background:#fff;border-radius:12px;padding:24px;border:1px solid #EBE8E1">
<p style="color:#4A4A68">Assalamualaikum, kod OTP anda:</p>
<div style="text-align:center;margin:24px 0">
<div style="display:inline-block;background:#FFF9E6;border:2px solid #C8A23C;border-radius:12px;padding:16px 32px">
<span style="font-family:monospace;font-size:36px;font-weight:700;letter-spacing:8px;color:#856C28">{otp}</span>
</div></div>
<p style="color:#8A8AA3;font-size:13px;text-align:center">Sah <strong>10 minit</strong>. Jangan kongsikan kod ini.</p>
</div></div>"""
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json={
                    "sender": {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email},
                    "to": [{"email": email}],
                    "subject": "Kod OTP Pendaftaran Jodohku.my",
                    "htmlContent": html,
                },
                headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json"},
                timeout=10
            )
            if res.status_code not in (200, 201):
                print(f"[Brevo] Error {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Brevo] Exception: {e}")


async def send_reset_email(email: str, otp: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.brevo.com/v3/smtp/email",
                json={
                    "sender": {"name": settings.brevo_sender_name, "email": settings.brevo_sender_email},
                    "to": [{"email": email}],
                    "subject": "Set Semula Kata Laluan Jodohku.my",
                    "htmlContent": f"<p>Kod OTP: <strong>{otp}</strong> (sah 10 minit)</p>",
                },
                headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json"},
                timeout=10
            )
    except Exception as e:
        print(f"[Brevo] Reset email error: {e}")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_code_name(self) -> str:
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(chars) for _ in range(5))

    def _generate_otp(self) -> str:
        return f"{secrets.randbelow(1000000):06d}"

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    def _create_access_token(self, user_id: str, expires_minutes: int = None) -> str:
        expires = datetime.utcnow() + timedelta(
            minutes=expires_minutes or settings.jwt_access_token_expire_minutes
        )
        return jwt.encode(
            {"sub": user_id, "exp": expires, "type": "access"},
            settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def _create_refresh_token(self, user_id: str) -> str:
        expires = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        return jwt.encode(
            {"sub": user_id, "exp": expires, "type": "refresh"},
            settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

    def _compute_device_hash(self, device_info: dict) -> str:
        raw = f"{device_info.get('user_agent','')}{device_info.get('accept_language','')}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    async def register(self, email: str, password: str) -> dict:
        result = await self.db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.status == AccountStatus.PENDING_EKYC:
                # Resend OTP
                otp = self._generate_otp()
                redis = await get_redis()
                await redis.setex(f"otp:{email}", 600, json.dumps({"code": otp, "user_id": str(existing.id)}))
                await send_otp_email(email, otp)
                return {"user_id": existing.id}
            raise HTTPException(status_code=409, detail="Emel sudah didaftarkan.")

        # Generate unique code name
        code_name = self._generate_code_name()
        while True:
            check = await self.db.execute(select(User).where(User.code_name == code_name))
            if not check.scalar_one_or_none():
                break
            code_name = self._generate_code_name()

        user = User(
            email=email,
            hashed_password=self._hash_password(password),
            code_name=code_name,
            status=AccountStatus.PENDING_EKYC,
        )
        self.db.add(user)
        await self.db.flush()

        # Store OTP in Redis
        otp = self._generate_otp()
        redis = await get_redis()
        await redis.setex(f"otp:{email}", 600, json.dumps({"code": otp, "user_id": str(user.id)}))

        # Send via Brevo
        await send_otp_email(email, otp)

        return {"user_id": user.id}

    async def verify_otp(self, email: str, otp_code: str) -> dict:
        redis = await get_redis()
        raw = await redis.get(f"otp:{email}")

        if not raw:
            raise HTTPException(status_code=400, detail="OTP tidak sah atau telah tamat tempoh. Sila daftar semula.")

        otp_data = json.loads(raw)

        if otp_data["code"] != otp_code:
            raise HTTPException(status_code=400, detail="Kod OTP salah.")

        await redis.delete(f"otp:{email}")

        ekyc_token = self._create_access_token(otp_data["user_id"], expires_minutes=30)
        return {"ekyc_token": ekyc_token}

    async def login(self, email: str, password: str, device_info: dict) -> dict:
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not self._verify_password(password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Emel atau kata laluan tidak sah.")

        if user.status == AccountStatus.SUSPENDED:
            raise HTTPException(status_code=403, detail="Akaun anda telah digantung.")

        if user.status == AccountStatus.DELETED:
            raise HTTPException(status_code=410, detail="Akaun telah dipadamkan.")

        device_hash = self._compute_device_hash(device_info)
        if user.device_fingerprints is None:
            user.device_fingerprints = []
        if device_hash not in [d.get("hash") for d in (user.device_fingerprints or [])]:
            user.device_fingerprints = (user.device_fingerprints or []) + [{
                "hash": device_hash,
                "first_seen": datetime.utcnow().isoformat(),
                "ip": device_info.get("ip", ""),
            }]

        user.last_active_at = datetime.utcnow()
        await self.db.flush()

        user_id_str = str(user.id)
        return {
            "access_token": self._create_access_token(user_id_str),
            "refresh_token": self._create_refresh_token(user_id_str),
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
            "user_id": user.id,
            "code_name": user.code_name,
            "current_tier": user.current_tier.value,
            "profile_completion": user.profile_completion,
        }

    async def refresh(self, refresh_token: str) -> dict:
        try:
            payload = jwt.decode(refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            if payload.get("type") != "refresh":
                raise HTTPException(status_code=401, detail="Token tidak sah.")
            user_id = payload["sub"]
            result = await self.db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=401, detail="Pengguna tidak ditemui.")
            return {
                "access_token": self._create_access_token(user_id),
                "refresh_token": self._create_refresh_token(user_id),
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
        pass

    async def send_password_reset(self, email: str):
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            otp = self._generate_otp()
            redis = await get_redis()
            await redis.setex(f"otp_reset:{email}", 600, json.dumps({"code": otp}))
            await send_reset_email(email, otp)

    async def reset_password(self, email: str, otp_code: str, new_password: str):
        redis = await get_redis()
        raw = await redis.get(f"otp_reset:{email}")
        if not raw:
            raise HTTPException(status_code=400, detail="OTP tidak sah atau tamat tempoh.")
        otp_data = json.loads(raw)
        if otp_data["code"] != otp_code:
            raise HTTPException(status_code=400, detail="Kod OTP salah.")
        await redis.delete(f"otp_reset:{email}")
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            user.hashed_password = self._hash_password(new_password)
