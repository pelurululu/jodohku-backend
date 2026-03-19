"""
JODOHKU.MY — Payment & Subscription Routes
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
async def get_plans(db: AsyncSession = Depends(get_db)):
    service = SubscriptionService(db)
    return await service.get_all_plans()


@router.post("/create-bill")
async def create_payment(
    request: CreatePaymentRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    result = await service.create_bill(
        user_id=current_user.id,
        tier=request.tier,
        promo_code=request.promo_code,
    )

    # Return whatever the service gives — don't assume keys
    if not result:
        raise HTTPException(status_code=500, detail="Gagal membuat bil pembayaran.")

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return result


@router.get("/return")
async def payment_return(
    billcode: str = None,
    status_id: str = None,
    order_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle redirect back from payment gateway."""
    if status_id == "1":
        return {"status": "success", "message": "Pembayaran berjaya! Langganan anda telah diaktifkan."}
    return {"status": "pending", "message": "Pembayaran sedang diproses."}


@router.post("/callback")
@router.post("/callback/toyyibpay")
async def toyyibpay_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """ToyyibPay payment callback."""
    try:
        form_data = await request.form()
        data = dict(form_data)
    except Exception:
        data = await request.json()

    service = PaymentService(db)
    return await service.process_callback(gateway="toyyibpay", data=data)


@router.post("/callback/billplz")
async def billplz_callback(request: Request, db: AsyncSession = Depends(get_db)):
    form_data = await request.form()
    service = PaymentService(db)
    return await service.process_callback(gateway="billplz", data=dict(form_data))


@router.post("/callback/senangpay")
async def senangpay_callback(request: Request, db: AsyncSession = Depends(get_db)):
    form_data = await request.form()
    service = PaymentService(db)
    return await service.process_callback(gateway="senangpay", data=dict(form_data))


@router.get("/subscription")
async def get_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    return await service.get_active_subscription(current_user.id)


@router.get("/transactions")
async def get_transactions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    return await service.get_user_transactions(current_user.id)


@router.post("/refund")
async def request_refund(
    request: RefundRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PaymentService(db)
    return await service.request_refund(
        user_id=current_user.id,
        reason=request.reason,
    )


@router.get("/golden-tickets")
async def get_golden_tickets(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    return await service.get_golden_tickets(current_user.id)


@router.post("/golden-ticket/redeem")
async def redeem_golden_ticket(
    code: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = SubscriptionService(db)
    return await service.redeem_golden_ticket(current_user.id, code)
