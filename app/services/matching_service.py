"""
JODOHKU.MY — Matching Service
Cosine similarity engine with weighted multi-component scoring

S(A,B) = (Σ Aᵢ Bᵢ) / (√Σ Aᵢ² × √Σ Bᵢ²)

Weighting:
- Psychometric quiz:     40%
- Values & Red Flags:    25%
- Demographics:          20%
- Hobbies & Lifestyle:   10%
- Verification badges:    5%
"""

import math
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserProfile, UserPreference, AccountStatus, SubscriptionTier
from app.models.quiz import PsychometricScore
from app.models.matching import Match, MatchInteraction, Favorite, MatchStatus, InteractionType


# ═══════════════════════════════════════════
#  COSINE SIMILARITY CORE
# ═══════════════════════════════════════════

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Compute cosine similarity between two vectors.
    Returns value between 0.0 and 1.0.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return dot_product / (magnitude_a * magnitude_b)


def compute_values_compatibility(values_a: list, values_b: list, flags_a: list, flags_b: list) -> float:
    """
    Compute values and red flags compatibility.
    - Shared values increase score
    - Matching red flags increase score (both dislike same things)
    - One person's value being the other's red flag = severe penalty
    """
    if not values_a or not values_b:
        return 0.5  # Neutral if data missing
    
    # Shared values (Jaccard similarity)
    shared_values = len(set(values_a) & set(values_b))
    total_values = len(set(values_a) | set(values_b))
    value_score = shared_values / max(total_values, 1)
    
    # Shared red flags
    shared_flags = len(set(flags_a or []) & set(flags_b or []))
    total_flags = len(set(flags_a or []) | set(flags_b or []))
    flag_score = shared_flags / max(total_flags, 1)
    
    return (value_score * 0.6) + (flag_score * 0.4)


def compute_demographic_score(profile_a, profile_b, prefs_a, prefs_b) -> float:
    """
    Score demographic compatibility against preferences.
    - Age within preferred range
    - Location match
    - Education level meets minimum
    - Income meets minimum
    """
    scores = []
    
    # Age compatibility
    if profile_a and profile_b and profile_a.date_of_birth and profile_b.date_of_birth:
        from datetime import date
        age_a = (date.today() - profile_a.date_of_birth).days // 365
        age_b = (date.today() - profile_b.date_of_birth).days // 365
        
        age_ok_a = True
        if prefs_a:
            if prefs_a.preferred_age_min and age_b < prefs_a.preferred_age_min:
                age_ok_a = False
            if prefs_a.preferred_age_max and age_b > prefs_a.preferred_age_max:
                age_ok_a = False
        
        age_ok_b = True
        if prefs_b:
            if prefs_b.preferred_age_min and age_a < prefs_b.preferred_age_min:
                age_ok_b = False
            if prefs_b.preferred_age_max and age_a > prefs_b.preferred_age_max:
                age_ok_b = False
        
        scores.append(1.0 if (age_ok_a and age_ok_b) else 0.3)
    
    # State match
    if profile_a and profile_b:
        if profile_a.state_of_residence == profile_b.state_of_residence:
            scores.append(1.0)
        elif prefs_a and prefs_a.preferred_states:
            state_b = profile_b.state_of_residence
            scores.append(1.0 if state_b and state_b.value in prefs_a.preferred_states else 0.5)
        else:
            scores.append(0.6)
    
    # Education
    if profile_a and profile_b and profile_a.education_level and profile_b.education_level:
        scores.append(0.8)  # Simplified: any education data = base compatibility
    
    return sum(scores) / max(len(scores), 1)


def compute_hobby_score(hobbies_a: list, hobbies_b: list) -> float:
    """Jaccard similarity on hobby selections."""
    if not hobbies_a or not hobbies_b:
        return 0.5
    
    shared = len(set(hobbies_a) & set(hobbies_b))
    total = len(set(hobbies_a) | set(hobbies_b))
    return shared / max(total, 1)


def compute_badge_bonus(user_a: User, user_b: User) -> float:
    """Bonus score for verification badges."""
    bonus = 0.0
    if user_a.is_verified_t20:
        bonus += 0.5
    if user_b.is_verified_t20:
        bonus += 0.5
    if user_a.profile_completion >= 100:
        bonus += 0.25
    if user_b.profile_completion >= 100:
        bonus += 0.25
    return min(bonus / 1.5, 1.0)  # Normalize to 0-1


# ═══════════════════════════════════════════
#  MATCHING SERVICE
# ═══════════════════════════════════════════

class MatchingService:
    """
    Weights:
    - Psychometric: 40%
    - Values/RedFlags: 25%
    - Demographics: 20%
    - Hobbies: 10%
    - Badges: 5%
    
    Threshold: S(A,B) >= 0.85 to appear in gallery.
    """
    
    WEIGHT_PSYCHOMETRIC = 0.40
    WEIGHT_VALUES = 0.25
    WEIGHT_DEMOGRAPHIC = 0.20
    WEIGHT_HOBBIES = 0.10
    WEIGHT_BADGES = 0.05
    THRESHOLD = 0.30  # Lowered for testing — raise to 0.85 in production

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_match_score(self, user_a_id: UUID, user_b_id: UUID) -> dict:
        """
        Compute full weighted compatibility score between two users.
        Returns score breakdown and total.
        """
        # Fetch all required data
        user_a = await self.db.get(User, user_a_id)
        user_b = await self.db.get(User, user_b_id)
        
        profile_a = await self._get_profile(user_a_id)
        profile_b = await self._get_profile(user_b_id)
        
        prefs_a = await self._get_preferences(user_a_id)
        prefs_b = await self._get_preferences(user_b_id)
        
        psych_a = await self._get_psychometric(user_a_id)
        psych_b = await self._get_psychometric(user_b_id)

        # 1. Psychometric (cosine similarity on quiz vectors)
        psych_score = 0.0
        if psych_a and psych_b and psych_a.vector and psych_b.vector:
            psych_score = cosine_similarity(psych_a.vector, psych_b.vector)

        # 2. Values & Red Flags
        values_score = compute_values_compatibility(
            profile_a.desired_values if profile_a else [],
            profile_b.desired_values if profile_b else [],
            profile_a.red_flags if profile_a else [],
            profile_b.red_flags if profile_b else [],
        )

        # 3. Demographics
        demo_score = compute_demographic_score(profile_a, profile_b, prefs_a, prefs_b)

        # 4. Hobbies
        hobby_score = compute_hobby_score(
            profile_a.hobbies if profile_a else [],
            profile_b.hobbies if profile_b else [],
        )

        # 5. Badges
        badge_score = compute_badge_bonus(user_a, user_b) if user_a and user_b else 0.0

        # Weighted total
        total = (
            psych_score * self.WEIGHT_PSYCHOMETRIC +
            values_score * self.WEIGHT_VALUES +
            demo_score * self.WEIGHT_DEMOGRAPHIC +
            hobby_score * self.WEIGHT_HOBBIES +
            badge_score * self.WEIGHT_BADGES
        )

        return {
            "total": round(total, 4),
            "breakdown": {
                "psychometric": round(psych_score, 4),
                "values_redflags": round(values_score, 4),
                "demographic": round(demo_score, 4),
                "hobbies": round(hobby_score, 4),
                "badges": round(badge_score, 4),
            }
        }

    async def get_gallery(
        self, user_id: UUID, tier: str, filters, page: int, page_size: int
    ) -> dict:
        """
        Get Bilik Pameran profiles for user.
        Only returns matches >= 0.85 threshold.
        Applies tier-based daily view limits.
        """
        # TODO: Check daily view quota based on tier
        # Rahmah: 10/day, Gold: 30/day, Platinum+: unlimited
        
        offset = (page - 1) * page_size
        
        # Query pre-computed matches above threshold
        query = (
            select(Match)
            .where(
                or_(
                    Match.user_a_id == user_id,
                    Match.user_b_id == user_id,
                ),
                Match.compatibility_score >= self.THRESHOLD,
            )
            .order_by(desc(Match.compatibility_score))
            .offset(offset)
            .limit(page_size)
        )
        
        result = await self.db.execute(query)
        matches = result.scalars().all()
        
        # Build profile responses
        profiles = []
        for match in matches:
            target_id = match.user_b_id if match.user_a_id == user_id else match.user_a_id
            profile = await self._build_profile_response(
                target_id, viewer_tier=tier, compatibility=match.compatibility_score,
                wingman_tip_ms=match.wingman_tip_ms,
            )
            if profile:
                profiles.append(profile)
        
        # Count total
        count_query = select(func.count()).select_from(Match).where(
            or_(Match.user_a_id == user_id, Match.user_b_id == user_id),
            Match.compatibility_score >= self.THRESHOLD,
        )
        total = (await self.db.execute(count_query)).scalar() or 0
        
        return {
            "profiles": profiles,
            "total_count": total,
            "page": page,
            "page_size": page_size,
            "has_next": offset + page_size < total,
        }

    async def perform_action(
        self, actor_id: UUID, target_id: UUID, action: str, actor_tier: str
    ) -> dict:
        """Handle gallery actions: like, reject, block, save_favorite, lamar."""
        
        # Log interaction
        interaction_map = {
            "like": InteractionType.LIKE,
            "reject": InteractionType.REJECT,
            "block": InteractionType.BLOCK,
            "save_favorite": InteractionType.SAVE_FAVORITE,
            "lamar": InteractionType.LAMAR,
        }
        
        interaction = MatchInteraction(
            actor_id=actor_id,
            target_id=target_id,
            interaction_type=interaction_map.get(action, InteractionType.VIEW),
        )
        self.db.add(interaction)
        
        if action == "save_favorite":
            fav = Favorite(user_id=actor_id, target_id=target_id)
            self.db.add(fav)
        
        if action == "block":
            # Update match status
            match = await self._find_match(actor_id, target_id)
            if match:
                if match.user_a_id == actor_id:
                    match.status_a = MatchStatus.BLOCKED
                else:
                    match.status_b = MatchStatus.BLOCKED
        
        await self.db.flush()
        return {"action": action, "success": True}

    async def get_favorites(self, user_id: UUID, page: int) -> dict:
        offset = (page - 1) * 20
        query = (
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(desc(Favorite.created_at))
            .offset(offset)
            .limit(20)
        )
        result = await self.db.execute(query)
        favorites = result.scalars().all()
        
        profiles = []
        for fav in favorites:
            profile = await self._build_profile_response(fav.target_id)
            if profile:
                profiles.append(profile)
        
        return {"profiles": profiles, "page": page}

    async def get_who_liked_me(self, user_id: UUID, tier: str) -> dict:
        query = select(MatchInteraction).where(
            MatchInteraction.target_id == user_id,
            MatchInteraction.interaction_type == InteractionType.LIKE,
        ).order_by(desc(MatchInteraction.created_at))
        
        result = await self.db.execute(query)
        likes = result.scalars().all()
        
        if tier == SubscriptionTier.RAHMAH.value:
            return {"count": len(likes), "profiles": [], "tier_locked": True}
        
        profiles = []
        for like in likes[:50]:
            profile = await self._build_profile_response(like.actor_id, viewer_tier=tier)
            if profile:
                profiles.append(profile)
        
        return {"count": len(likes), "profiles": profiles, "tier_locked": False}

    async def get_compatibility_report(self, user_id: UUID, target_code: str) -> dict:
        target = await self.db.execute(
            select(User).where(User.code_name == target_code)
        )
        target_user = target.scalar_one_or_none()
        if not target_user:
            return {"error": "Pengguna tidak ditemui."}
        
        return await self.compute_match_score(user_id, target_user.id)

    # ─── Private Helpers ───

    async def _get_profile(self, user_id: UUID):
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_preferences(self, user_id: UUID):
        result = await self.db.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_psychometric(self, user_id: UUID):
        result = await self.db.execute(
            select(PsychometricScore).where(PsychometricScore.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _find_match(self, user_a_id: UUID, user_b_id: UUID):
        result = await self.db.execute(
            select(Match).where(
                or_(
                    and_(Match.user_a_id == user_a_id, Match.user_b_id == user_b_id),
                    and_(Match.user_a_id == user_b_id, Match.user_b_id == user_a_id),
                )
            )
        )
        return result.scalar_one_or_none()

    async def _build_profile_response(
        self, user_id: UUID, viewer_tier: str = None,
        compatibility: float = None, wingman_tip_ms: str = None
    ) -> dict:
        user = await self.db.get(User, user_id)
        if not user or user.status != AccountStatus.ACTIVE:
            return None
        
        profile = await self._get_profile(user_id)
        
        # Calculate age
        age = None
        if profile and profile.date_of_birth:
            from datetime import date
            age = (date.today() - profile.date_of_birth).days // 365
        
        is_blurred = viewer_tier == SubscriptionTier.RAHMAH.value if viewer_tier else False
        
        return {
            "user_id": str(user.id),
            "code_name": user.code_name,
            "display_name": profile.display_name if profile else None,
            "gender": profile.gender.value if profile and profile.gender else None,
            "age": age,
            "state_of_residence": profile.state_of_residence.value if profile and profile.state_of_residence else None,
            "education_level": profile.education_level.value if profile and profile.education_level else None,
            "occupation": profile.occupation if profile else None,
            "income_range": profile.income_range.value if profile and profile.income_range else None,
            "marital_status": profile.marital_status.value if profile and profile.marital_status else None,
            "bio_text": profile.bio_text if profile else None,
            "hobbies": profile.hobbies if profile else [],
            "current_tier": user.current_tier.value,
            "is_verified_t20": user.is_verified_t20,
            "profile_completion": user.profile_completion,
            "compatibility_score": compatibility,
            "wingman_tip": wingman_tip_ms,
            "photos": [],  # Populated by photo service
            "is_blurred": is_blurred,
        }


    async def compute_matches_for_user(self, user_id: UUID) -> int:
        """
        Compute/update match scores between this user and ALL other active users.
        Called after quiz answers saved. Writes to matches table.
        Returns number of matches computed.
        """
        from app.models.matching import Match, MatchStatus

        # Get all other active users
        result = await self.db.execute(
            select(User).where(
                User.id != user_id,
                User.status == AccountStatus.ACTIVE,
            )
        )
        other_users = result.scalars().all()

        computed = 0
        for other in other_users:
            # Skip same gender
            profile_self = await self._get_profile(user_id)
            profile_other = await self._get_profile(other.id)
            if (profile_self and profile_other and
                    profile_self.gender and profile_other.gender and
                    profile_self.gender == profile_other.gender):
                continue

            score_data = await self.compute_match_score(user_id, other.id)
            total = score_data["total"]

            # Canonical ordering — smaller UUID is always user_a
            a_id = user_id if str(user_id) < str(other.id) else other.id
            b_id = other.id if str(user_id) < str(other.id) else user_id

            existing = await self._find_match(a_id, b_id)
            if existing:
                existing.compatibility_score = total
                existing.score_breakdown = score_data["breakdown"]
            else:
                self.db.add(Match(
                    user_a_id=a_id,
                    user_b_id=b_id,
                    compatibility_score=total,
                    score_breakdown=score_data["breakdown"],
                    status_a=MatchStatus.SUGGESTED,
                    status_b=MatchStatus.SUGGESTED,
                ))
            computed += 1

        await self.db.flush()
        return computed
