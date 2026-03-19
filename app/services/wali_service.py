"""
JODOHKU.MY — Wali/Mahram Service
Real implementation: invitations, status, toggle mode
"""
import secrets
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.wali import WaliInvitation, WaliAccess, WaliRelation


class WaliService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_invitation(
        self,
        user_id: UUID,
        wali_email: str,
        wali_name: str,
        relation: str,
    ) -> dict:
        # Validate relation
        try:
            rel = WaliRelation(relation)
        except ValueError:
            rel = WaliRelation.OTHER_MAHRAM

        # Generate unique token
        token = secrets.token_urlsafe(32)

        invitation = WaliInvitation(
            user_id=user_id,
            wali_email=wali_email,
            wali_name=wali_name,
            relation=rel,
            token=token,
        )
        self.db.add(invitation)
        await self.db.flush()

        # TODO: Send invitation email via Brevo
        # For now just return success
        print(f"[Wali] Invitation sent to {wali_email}, token: {token}")

        return {"invitation_id": invitation.id, "token": token}

    async def get_status(self, user_id: UUID) -> dict:
        user = await self.db.get(User, user_id)
        if not user:
            return {"wali_mode_enabled": False, "invitations": []}

        # Get all invitations
        result = await self.db.execute(
            select(WaliInvitation).where(
                WaliInvitation.user_id == user_id,
                WaliInvitation.is_revoked == False,
            )
        )
        invitations = result.scalars().all()

        return {
            "wali_mode_enabled": user.wali_mode_enabled,
            "invitations": [
                {
                    "id": str(inv.id),
                    "wali_email": inv.wali_email,
                    "wali_name": inv.wali_name,
                    "relation": inv.relation.value,
                    "is_accepted": inv.is_accepted,
                    "created_at": inv.created_at.isoformat(),
                }
                for inv in invitations
            ],
        }

    async def toggle_mode(self, user_id: UUID, enabled: bool):
        user = await self.db.get(User, user_id)
        if user:
            user.wali_mode_enabled = enabled
            await self.db.flush()

    async def revoke_access(self, user_id: UUID, invitation_id: UUID):
        result = await self.db.execute(
            select(WaliInvitation).where(
                WaliInvitation.id == invitation_id,
                WaliInvitation.user_id == user_id,
            )
        )
        inv = result.scalar_one_or_none()
        if inv:
            inv.is_revoked = True
            inv.revoked_at = datetime.utcnow()
            await self.db.flush()

    async def wali_login(self, email: str, password: str, token: str) -> dict:
        # Find invitation by token
        result = await self.db.execute(
            select(WaliInvitation).where(WaliInvitation.token == token)
        )
        inv = result.scalar_one_or_none()
        if not inv:
            raise HTTPException(status_code=401, detail="Token jemputan tidak sah.")
        if inv.is_revoked:
            raise HTTPException(status_code=401, detail="Jemputan telah dibatalkan.")

        # Simple wali access — return read-only token
        return {
            "message": "Log masuk wali berjaya.",
            "wali_email": inv.wali_email,
            "user_id": str(inv.user_id),
            "access_type": "read_only",
        }

    async def get_wali_dashboard(self, user_id: UUID) -> dict:
        user = await self.db.get(User, user_id)
        if not user:
            return {}

        return {
            "user_code_name": user.code_name,
            "wali_mode_enabled": user.wali_mode_enabled,
            "profile_completion": user.profile_completion,
            "message": "Dashboard wali — ciri penuh akan tersedia tidak lama lagi.",
        }
