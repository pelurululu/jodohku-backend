"""
JODOHKU.MY — Payment & Subscription Service
Real implementation: ToyyibPay integration, subscription management
"""
import uuid
import httpx
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.subscription import (
    Subscription, Transaction, TierConfig, GoldenTicket,
    PaymentGateway, PaymentStatus, TransactionType
)
from app.models.user import User, SubscriptionTier

settings = get_settings()

TIER_DURATIONS = {
    SubscriptionTier.RAHMAH: 7,
    SubscriptionTier.GOLD: 30,
    SubscriptionTier.PLATINUM: 60,
    SubscriptionTier.PREMIUM: 90,
    SubscriptionTier.SOVEREIGN: 30,
}

TIER_PRICES = {
    SubscriptionTier.RAHMAH: 0.0,
    SubscriptionTier.GOLD: 39.99,
    SubscriptionTier.PLATINUM: 69.99,
    SubscriptionTier.PREMIUM: 101.99,
    SubscriptionTier.SOVEREIGN: 1299.99,
}


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_bill(self, user_id: UUID, tier: str, promo_code: str = None) -> dict:
        try:
            tier_enum = SubscriptionTier(tier)
        except ValueError:
            return {"error": "Tier tidak sah."}

        price = TIER_PRICES.get(tier_enum, 0)
        duration = TIER_DURATIONS.get(tier_enum, 30)

        # Create transaction record
        txn = Transaction(
            user_id=user_id,
            transaction_type=TransactionType.SUBSCRIPTION,
            amount_myr=price,
            discount_applied=0.0,
            final_amount_myr=price,
            gateway=PaymentGateway.TOYYIBPAY,
            status=PaymentStatus.PENDING,
        )
        self.db.add(txn)
        await self.db.flush()

        # Free tier — activate immediately
        if price == 0:
            await self._activate_subscription(user_id, tier_enum, duration, txn.id)
            txn.status = PaymentStatus.SUCCESS
            txn.completed_at = datetime.utcnow()
            await self.db.flush()
            return {
                "success": True,
                "tier": tier,
                "payment_url": None,
                "transaction_id": str(txn.id),
                "message": "Pelan Rahmah diaktifkan.",
            }

        # Create ToyyibPay bill
        bill_code = await self._create_toyyibpay_bill(
            amount=price,
            transaction_id=str(txn.id),
            description=f"Jodohku.my - {tier_enum.value.capitalize()} {duration} Hari",
        )

        if bill_code:
            txn.gateway_bill_code = bill_code
            await self.db.flush()
            return {
                "success": True,
                "tier": tier,
                "payment_url": f"{settings.toyyibpay_base_url}/{bill_code}",
                "transaction_id": str(txn.id),
                "bill_code": bill_code,
                "amount": price,
                "duration_days": duration,
            }

        return {
            "success": False,
            "error": "Gagal membuat bil pembayaran. Cuba semula.",
        }

    async def process_callback(self, gateway: str, data: dict) -> dict:
        bill_code = data.get("billcode") or data.get("bill_code", "")
        status_code = str(data.get("status_id", data.get("status", "0")))
        ref_no = data.get("refno") or data.get("transaction_id", "")

        # Find transaction by bill code
        result = await self.db.execute(
            select(Transaction).where(Transaction.gateway_bill_code == bill_code)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            return {"status": "not_found"}

        # ToyyibPay: status_id=1 = success
        if status_code == "1":
            txn.status = PaymentStatus.SUCCESS
            txn.gateway_reference = ref_no
            txn.completed_at = datetime.utcnow()
            await self.db.flush()

            # Get tier from amount
            tier_enum = self._amount_to_tier(float(txn.final_amount_myr))
            duration = TIER_DURATIONS.get(tier_enum, 30)
            await self._activate_subscription(txn.user_id, tier_enum, duration, txn.id)
        else:
            txn.status = PaymentStatus.FAILED
            await self.db.flush()

        return {"status": "processed"}

    async def get_user_transactions(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(desc(Transaction.created_at))
            .limit(20)
        )
        txns = result.scalars().all()
        return {
            "transactions": [
                {
                    "id": str(t.id),
                    "type": t.transaction_type.value,
                    "amount": float(t.final_amount_myr),
                    "status": t.status.value,
                    "gateway": t.gateway.value,
                    "created_at": t.created_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                }
                for t in txns
            ]
        }

    async def request_refund(self, user_id: UUID, reason: str = None) -> dict:
        # Get active subscription
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return {"success": False, "reason": "Tiada langganan aktif."}
        if not sub.refund_eligible:
            return {"success": False, "reason": "Langganan ini tidak layak untuk bayaran balik."}
        if sub.conversations_started > 0:
            return {"success": False, "reason": "Sudah menggunakan ciri sembang, tidak layak refund."}

        # Deactivate subscription
        sub.is_active = False
        # Reset user to Rahmah
        user = await self.db.get(User, user_id)
        if user:
            user.current_tier = SubscriptionTier.RAHMAH
        await self.db.flush()

        return {"success": True, "message": "Permintaan refund diterima. Diproses dalam 7 hari bekerja."}

    # ── Helpers ──

    async def _create_toyyibpay_bill(self, amount: float, transaction_id: str, description: str) -> Optional[str]:
        if not settings.toyyibpay_secret_key or not settings.toyyibpay_category_code:
            print("[ToyyibPay] TOYYIBPAY_SECRET_KEY or TOYYIBPAY_CATEGORY_CODE not set in environment.")
            return None
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.toyyibpay_base_url}/index.php/api/createBill",
                    data={
                        "userSecretKey": settings.toyyibpay_secret_key,
                        "categoryCode": settings.toyyibpay_category_code,
                        "billName": "Jodohku.my",
                        "billDescription": description[:150],
                        "billPriceSetting": 1,
                        "billPayorInfo": 1,
                        "billAmount": int(amount * 100),  # In sen
                        "billReturnUrl": f"{settings.backend_url}/api/v1/payment/return",
                        "billCallbackUrl": f"{settings.backend_url}/api/v1/payment/callback",
                        "billExternalReferenceNo": transaction_id,
                        "billTo": "Pelanggan Jodohku.my",
                        "billEmail": "",
                        "billPhone": "",
                        "billSplitPayment": 0,
                        "billPaymentChannel": 0,
                        "billContentEmail": f"Terima kasih kerana melanggan Jodohku.my",
                        "billChargeToCustomer": 0,
                    },
                    timeout=15,
                )
                data = res.json()
                if isinstance(data, list) and data:
                    return data[0].get("BillCode")
        except Exception as e:
            print(f"[ToyyibPay] Error: {e}")
        return None

    def _amount_to_tier(self, amount: float) -> SubscriptionTier:
        if amount <= 40:
            return SubscriptionTier.GOLD
        elif amount <= 70:
            return SubscriptionTier.PLATINUM
        elif amount <= 102:
            return SubscriptionTier.PREMIUM
        elif amount > 1000:
            return SubscriptionTier.SOVEREIGN
        return SubscriptionTier.GOLD

    async def _activate_subscription(self, user_id: UUID, tier: SubscriptionTier, duration: int, transaction_id: UUID):
        # Deactivate existing subscriptions
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.is_active == True,
            )
        )
        for sub in result.scalars().all():
            sub.is_active = False

        # Create new subscription
        now = datetime.utcnow()
        sub = Subscription(
            user_id=user_id,
            tier=tier,
            starts_at=now,
            expires_at=now + timedelta(days=duration),
            transaction_id=transaction_id,
            is_active=True,
            refund_eligible=True,
        )
        self.db.add(sub)

        # Update user tier
        user = await self.db.get(User, user_id)
        if user:
            user.current_tier = tier
        await self.db.flush()


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_plans(self) -> dict:
        result = await self.db.execute(
            select(TierConfig).where(TierConfig.is_active == True)
        )
        tiers = result.scalars().all()

        if not tiers:
            # Return hardcoded plans if DB not seeded yet
            return {"plans": [
                {"tier": "rahmah", "price_myr": 0.0, "duration_days": 7, "badge_label": "Rahmah"},
                {"tier": "gold", "price_myr": 39.99, "duration_days": 30, "badge_label": "Gold"},
                {"tier": "platinum", "price_myr": 69.99, "duration_days": 60, "badge_label": "Platinum"},
                {"tier": "premium", "price_myr": 101.99, "duration_days": 90, "badge_label": "Premium"},
                {"tier": "sovereign", "price_myr": 1299.99, "duration_days": 30, "badge_label": "Sovereign"},
            ]}

        return {
            "plans": [
                {
                    "tier": t.tier.value,
                    "price_myr": float(t.price_myr),
                    "duration_days": t.duration_days,
                    "daily_profile_views": t.daily_profile_views,
                    "max_concurrent_chats": t.max_concurrent_chats,
                    "has_clear_photos": t.has_clear_photos,
                    "has_whatsapp_access": t.has_whatsapp_access,
                    "has_priority_search": t.has_priority_search,
                    "has_video_taaruf": t.has_video_taaruf,
                    "has_ads_free": t.has_ads_free,
                    "badge_label": t.badge_label,
                    "badge_color": t.badge_color,
                }
                for t in tiers
            ]
        }

    async def get_active_subscription(self, user_id: UUID) -> dict:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id, Subscription.is_active == True)
            .order_by(desc(Subscription.created_at))
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return {"active": False, "tier": "rahmah"}

        days_remaining = (sub.expires_at - datetime.utcnow()).days if sub.expires_at else 0

        return {
            "active": True,
            "tier": sub.tier.value,
            "starts_at": sub.starts_at.isoformat(),
            "expires_at": sub.expires_at.isoformat(),
            "days_remaining": max(days_remaining, 0),
            "is_trial": sub.is_trial,
            "refund_eligible": sub.refund_eligible,
        }

    async def get_golden_tickets(self, user_id: UUID) -> dict:
        from datetime import date
        current_month = date.today().strftime("%Y-%m")
        result = await self.db.execute(
            select(GoldenTicket).where(
                GoldenTicket.owner_id == user_id,
                GoldenTicket.issued_month == current_month,
            )
        )
        tickets = result.scalars().all()
        return {
            "tickets": [
                {
                    "id": str(t.id),
                    "code": t.code,
                    "is_redeemed": t.is_redeemed,
                    "redeemed_by": str(t.redeemed_by_id) if t.redeemed_by_id else None,
                }
                for t in tickets
            ]
        }

    async def redeem_golden_ticket(self, user_id: UUID, code: str) -> dict:
        result = await self.db.execute(
            select(GoldenTicket).where(GoldenTicket.code == code)
        )
        ticket = result.scalar_one_or_none()
        if not ticket:
            return {"success": False, "reason": "Kod tidak sah."}
        if ticket.is_redeemed:
            return {"success": False, "reason": "Kod sudah digunakan."}
        if ticket.owner_id == user_id:
            return {"success": False, "reason": "Anda tidak boleh menggunakan kod anda sendiri."}

        ticket.is_redeemed = True
        ticket.redeemed_by_id = user_id
        ticket.redeemed_at = datetime.utcnow()
        await self.db.flush()

        # Give 7 days free Gold to redeemer
        pay_svc = PaymentService(self.db)
        await pay_svc._activate_subscription(user_id, SubscriptionTier.GOLD, 7, ticket.id)

        return {"success": True, "message": "Tahniah! 7 hari Gold diberikan."}
