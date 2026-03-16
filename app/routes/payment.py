"""
JODOHKU.MY — Payment & Subscription Routes
ToyyibPay primary + Billplz/SenangPay failover
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    SubscriptionPlanResponse, CreatePaymentRequest,
    SubscriptionResponse, RefundRequest
)
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/payment", tags=["Payment & Subscription"])


@router.get("/plans")
async def get_plans(
    db: AsyncSession = Depends(get_db),
):
    """
    Get all subscription plans with features.
    
    Tiers:
    - Rahmah (Free, 7 days)
    - Gold (RM39.99, 30 days)
    - Platinum (RM69.99, 60 days — 12% savings)
    - Premium (RM101.99, 90 days — 15% savings)
    - Sovereign Black Card (RM1,299.99, 30 days)
    """
    service = SubscriptionService(db)
    return await service.get_all_plans()


@router.post("/create-bill")
async def create_payment(
    request: CreatePaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create payment bill.
    
    Flow:
    1. Create bill via ToyyibPay
    2. If ToyyibPay fails within 3 seconds → failover to Billplz
    3. If Billplz fails → failover to SenangPay
    4. Return payment URL for redirect
    
    Promo codes applied here (first-time 20%, Ramadan, referral).
    """
    service = PaymentService(db)
    result = await service.create_bill(
        user_id=current_user.id,
        tier=request.tier,
        promo_code=request.promo_code,
    )
    return {
        "payment_url": result["payment_url"],
        "bill_code": result["bill_code"],
        "gateway": result["gateway"],
        "amount": result["amount"],
        "original_amount": result.get("original_amount"),
        "discount_applied": result.get("discount_applied", 0),
    }


@router.post("/callback/toyyibpay")
async def toyyibpay_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    ToyyibPay payment callback.
    Activates subscription on successful payment.
    """
    form_data = await request.form()
    service = PaymentService(db)
    return await service.process_callback(
        gateway="toyyibpay",
        data=dict(form_data),
    )


@router.post("/callback/billplz")
async def billplz_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Billplz payment callback (failover gateway)."""
    form_data = await request.form()
    service = PaymentService(db)
    return await service.process_callback(
        gateway="billplz",
        data=dict(form_data),
    )


@router.post("/callback/senangpay")
async def senangpay_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """SenangPay payment callback (failover gateway)."""
    form_data = await request.form()
    service = PaymentService(db)
    return await service.process_callback(
        gateway="senangpay",
        data=dict(form_data),
    )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current subscription details."""
    service = SubscriptionService(db)
    return await service.get_active_subscription(current_user.id)


@router.get("/transactions")
async def get_transactions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment transaction history."""
    service = PaymentService(db)
    return await service.get_user_transactions(current_user.id)


@router.post("/refund")
async def request_refund(
    request: RefundRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request refund (CPA 1999 compliance).
    
    Eligible if:
    - Within 7 days of subscription
    - Less than 10 conversations started
    - Processing: 5-10 business days
    """
    service = PaymentService(db)
    return await service.request_refund(
        user_id=current_user.id,
        reason=request.reason,
    )


# ─── Golden Ticket ───

@router.get("/golden-tickets")
async def get_golden_tickets(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get user's Golden Ticket referral codes."""
    service = SubscriptionService(db)
    return await service.get_golden_tickets(current_user.id)


@router.post("/golden-ticket/redeem")
async def redeem_golden_ticket(
    code: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Redeem a Golden Ticket referral code."""
    service = SubscriptionService(db)
    return await service.redeem_golden_ticket(current_user.id, code)
