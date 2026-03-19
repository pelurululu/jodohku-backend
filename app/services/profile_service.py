"""
JODOHKU.MY — Profile Service
Real implementation reading/writing from database
"""
import uuid
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserProfile, UserPreference, AccountStatus, SubscriptionTier


class ProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_profile(self, user_id: UUID, viewer_id: UUID = None) -> dict:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Pengguna tidak ditemui.")

        profile = await self._get_profile(user_id)
        photos = []  # TODO: join with photos table when implemented

        age = None
        if profile and profile.date_of_birth:
            age = (date.today() - profile.date_of_birth).days // 365

        # Determine if viewer can see clear photos
        is_blurred = False
        if viewer_id and viewer_id != user_id:
            viewer = await self.db.get(User, viewer_id)
            if viewer and viewer.current_tier == SubscriptionTier.RAHMAH:
                is_blurred = True

        return {
            "user_id": str(user.id),
            "code_name": user.code_name,
            "display_name": profile.display_name if profile else None,
            "gender": profile.gender.value if profile and profile.gender else None,
            "age": age,
            "date_of_birth": profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None,
            "height_cm": profile.height_cm if profile else None,
            "weight_kg": profile.weight_kg if profile else None,
            "state_of_birth": profile.state_of_birth.value if profile and profile.state_of_birth else None,
            "state_of_residence": profile.state_of_residence.value if profile and profile.state_of_residence else None,
            "education_level": profile.education_level.value if profile and profile.education_level else None,
            "occupation": profile.occupation if profile else None,
            "occupation_category": profile.occupation_category if profile else None,
            "income_range": profile.income_range.value if profile and profile.income_range else None,
            "marital_status": profile.marital_status.value if profile and profile.marital_status else None,
            "dependants": profile.dependants if profile else None,
            "bio_text": profile.bio_text if profile else None,
            "hobbies": profile.hobbies if profile else [],
            "desired_values": profile.desired_values if profile else [],
            "red_flags": profile.red_flags if profile else [],
            "photos": photos,
            "current_tier": user.current_tier.value,
            "is_verified_t20": user.is_verified_t20,
            "profile_completion": user.profile_completion,
            "is_blurred": is_blurred,
            "is_online": user.last_active_at and (datetime.utcnow() - user.last_active_at).seconds < 300,
            "last_active": user.last_active_at.isoformat() if user.last_active_at else None,
            "status": user.status.value,
        }

    async def get_profile_by_code(self, code_name: str, viewer_id: UUID = None, viewer_tier: str = None) -> dict:
        result = await self.db.execute(select(User).where(User.code_name == code_name))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Profil tidak ditemui.")
        return await self.get_profile(user.id, viewer_id=viewer_id)

    async def update_profile(self, user_id: UUID, data) -> dict:
        profile = await self._get_profile(user_id)

        if not profile:
            profile = UserProfile(user_id=user_id, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            self.db.add(profile)

        # Update fields from request
        fields = [
            "display_name", "gender", "date_of_birth", "height_cm", "weight_kg",
            "state_of_birth", "state_of_residence", "education_level", "occupation",
            "occupation_category", "income_range", "marital_status", "dependants",
            "bio_text", "hobbies", "desired_values", "red_flags",
        ]
        for field in fields:
            val = getattr(data, field, None)
            if val is not None:
                setattr(profile, field, val)

        profile.updated_at = datetime.utcnow()
        await self.db.flush()

        # Recalculate completion
        completion = self._calc_completion(profile)
        user = await self.db.get(User, user_id)
        if user:
            user.profile_completion = completion
        await self.db.flush()

        return {"profile_completion": completion, "newly_unlocked": []}

    async def get_preferences(self, user_id: UUID) -> dict:
        result = await self.db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        prefs = result.scalar_one_or_none()
        if not prefs:
            return {}
        return {
            "preferred_age_min": prefs.preferred_age_min,
            "preferred_age_max": prefs.preferred_age_max,
            "preferred_states": prefs.preferred_states,
            "preferred_education_min": prefs.preferred_education_min,
            "preferred_income_min": prefs.preferred_income_min,
            "preferred_marital_status": prefs.preferred_marital_status,
            "preferred_height_min": prefs.preferred_height_min,
            "preferred_height_max": prefs.preferred_height_max,
        }

    async def update_preferences(self, user_id: UUID, data) -> dict:
        result = await self.db.execute(select(UserPreference).where(UserPreference.user_id == user_id))
        prefs = result.scalar_one_or_none()

        if not prefs:
            prefs = UserPreference(user_id=user_id)
            self.db.add(prefs)

        fields = [
            "preferred_age_min", "preferred_age_max", "preferred_states",
            "preferred_education_min", "preferred_income_min",
            "preferred_marital_status", "preferred_height_min", "preferred_height_max",
        ]
        for field in fields:
            val = getattr(data, field, None)
            if val is not None:
                setattr(prefs, field, val)

        await self.db.flush()
        return {"message": "Keutamaan dikemaskini."}

    async def get_completion_breakdown(self, user_id: UUID) -> dict:
        profile = await self._get_profile(user_id)
        if not profile:
            return {"completion": 0, "missing": ["display_name", "gender", "date_of_birth", "state_of_residence", "bio_text"]}

        missing = []
        if not profile.display_name: missing.append("display_name")
        if not profile.gender: missing.append("gender")
        if not profile.date_of_birth: missing.append("date_of_birth")
        if not profile.state_of_residence: missing.append("state_of_residence")
        if not profile.education_level: missing.append("education_level")
        if not profile.occupation: missing.append("occupation")
        if not profile.bio_text: missing.append("bio_text")
        if not profile.hobbies: missing.append("hobbies")

        return {
            "completion": self._calc_completion(profile),
            "missing": missing,
        }

    async def submit_t20_verification(self, user_id: UUID, file, doc_type: str) -> dict:
        # TODO: Store document and queue for admin review
        return {"message": "Dokumen diterima untuk semakan."}

    # ── Helpers ──

    async def _get_profile(self, user_id: UUID):
        result = await self.db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        return result.scalar_one_or_none()

    def _calc_completion(self, profile) -> int:
        if not profile:
            return 0
        fields = [
            profile.display_name, profile.gender, profile.date_of_birth,
            profile.state_of_residence, profile.education_level,
            profile.occupation, profile.income_range, profile.marital_status,
            profile.bio_text,
        ]
        list_fields = [profile.hobbies]
        filled = sum(1 for f in fields if f is not None)
        filled += sum(1 for f in list_fields if f and len(f) > 0)
        total = len(fields) + len(list_fields)
        return round((filled / total) * 100)
