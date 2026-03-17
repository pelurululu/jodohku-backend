"""
JODOHKU.MY — Account Service
Password change, account status management, blocking
"""
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, AccountStatus

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AccountService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def mark_married(self, user_id: UUID) -> dict:
        user = await self.db.get(User, user_id)
        if user:
            user.status = AccountStatus.MARRIED
            await self.db.flush()
        return {"message": "Profil disembunyikan selama 24 jam. Tahniah!"}

    async def pause_account(self, user_id: UUID) -> dict:
        user = await self.db.get(User, user_id)
        if user:
            user.status = AccountStatus.PAUSED
            await self.db.flush()
        return {"message": "Akaun dijeda. Anda boleh aktifkan semula bila-bila masa."}

    async def unpause_account(self, user_id: UUID) -> dict:
        user = await self.db.get(User, user_id)
        if user:
            user.status = AccountStatus.ACTIVE
            await self.db.flush()
        return {"message": "Akaun diaktifkan semula."}

    async def request_deletion(self, user_id: UUID) -> dict:
        user = await self.db.get(User, user_id)
        if user:
            user.status = AccountStatus.DELETED
            user.email = f"deleted_{user_id}@deleted.jodohku.my"
            await self.db.flush()
        return {"message": "Akaun akan dipadam dalam 30 hari (PDPA compliance)."}

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> dict:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Pengguna tidak ditemui.")
        if not pwd_context.verify(current_password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Kata laluan semasa tidak betul.")
        user.hashed_password = pwd_context.hash(new_password)
        await self.db.flush()
        return {"message": "Kata laluan berjaya ditukar."}

    async def block_user(self, user_id: UUID, target_user_id: UUID) -> dict:
        # This is handled in matching service via interaction
        return {"message": "Pengguna telah disekat."}
