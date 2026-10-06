"""Razorpay wallet top-ups for advertiser accounts."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db, require_role
from app.models.advertiser import AccountStatus, Advertiser
from app.models.payment import AdvertiserTopUp, TopUpStatus
from app.models.user import User
from app.schemas.payment import (
    AdvertiserTopUpOrderCreate,
    AdvertiserTopUpOrderOut,
    AdvertiserTopUpVerify,
    AdvertiserTopUpVerifyOut,
    AdvertiserWalletOut,
)

router = APIRouter(tags=["Advertiser Payments"])
_RAZORPAY_API = "https://api.razorpay.com/v1"


@router.get("/topups", summary="List advertiser top-ups")
async def list_topups(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role("admin")),
):
    rows = (
        await db.execute(
            select(AdvertiserTopUp, Advertiser.name, Advertiser.billing_email)
            .join(Advertiser, Advertiser.id == AdvertiserTopUp.advertiser_id)
            .order_by(AdvertiserTopUp.created_at.desc())
        )
    ).all()
    return [
        {
            "id": topup.id,
            "advertiser_id": topup.advertiser_id,
            "advertiser_name": advertiser_name,
            "billing_email": billing_email,
            "amount": topup.amount,
            "status": topup.status.value,
            "order_id": topup.order_id,
            "payment_id": topup.payment_id,
            "paid_at": topup.paid_at,
            "created_at": topup.created_at,
        }
        for topup, advertiser_name, billing_email in rows
    ]


def _credentials() -> tuple[str, str]:
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay is not configured")
    return settings.razorpay_key_id, settings.razorpay_key_secret.get_secret_value()


async def _advertiser_for_user(db: AsyncSession, user: User) -> Advertiser:
    advertiser = await db.get(Advertiser, user.advertiser_id) if user.advertiser_id else None
    if advertiser is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advertiser account not found")
    return advertiser


def _wallet(advertiser: Advertiser) -> AdvertiserWalletOut:
    return AdvertiserWalletOut(
        balance=advertiser.balance,
        credit_limit=advertiser.credit_limit,
        currency="INR",
    )


@router.get("/wallet", response_model=AdvertiserWalletOut)
async def get_wallet(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser")),
) -> AdvertiserWalletOut:
    return _wallet(await _advertiser_for_user(db, user))


@router.post("/orders", response_model=AdvertiserTopUpOrderOut)
async def create_topup_order(
    payload: AdvertiserTopUpOrderCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser")),
) -> AdvertiserTopUpOrderOut:
    advertiser = await _advertiser_for_user(db, user)
    if advertiser.status != AccountStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Advertiser account must be active to add funds")

    key_id, key_secret = _credentials()
    amount = payload.amount.quantize(Decimal("0.01"))
    amount_paise = int(amount * 100)
    receipt = f"adv_{advertiser.id}_{secrets.token_hex(8)}"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{_RAZORPAY_API}/orders",
                auth=httpx.BasicAuth(key_id, key_secret),
                json={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": {"advertiser_id": str(advertiser.id)},
                },
            )
            response.raise_for_status()
            razorpay_order = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not create a Razorpay order") from None

    order_id = razorpay_order.get("id")
    if not isinstance(order_id, str) or razorpay_order.get("amount") != amount_paise or razorpay_order.get("currency") != "INR":
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Razorpay returned an invalid order")

    db.add(
        AdvertiserTopUp(
            advertiser_id=advertiser.id,
            order_id=order_id,
            amount=amount,
            status=TopUpStatus.CREATED,
        )
    )
    await db.commit()
    return AdvertiserTopUpOrderOut(
        order_id=order_id,
        amount_paise=amount_paise,
        key_id=key_id,
        advertiser_name=advertiser.name,
        billing_email=advertiser.billing_email,
    )


async def _credit_topup(
    db: AsyncSession,
    *,
    order_id: str,
    payment_id: str,
    amount_paise: int,
    currency: str,
) -> AdvertiserWalletOut:
    topup = (
        await db.execute(
            select(AdvertiserTopUp).where(AdvertiserTopUp.order_id == order_id).with_for_update()
        )
    ).scalar_one_or_none()
    if topup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Top-up order not found")
    if currency != "INR" or amount_paise != int(topup.amount * 100):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment amount or currency does not match the order")
    if topup.status == TopUpStatus.PAID:
        if topup.payment_id != payment_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "Order has already been paid")
        advertiser = await db.get(Advertiser, topup.advertiser_id)
        if advertiser is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Advertiser account not found")
        return _wallet(advertiser)

    advertiser = (
        await db.execute(
            select(Advertiser).where(Advertiser.id == topup.advertiser_id).with_for_update()
        )
    ).scalar_one_or_none()
    if advertiser is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advertiser account not found")
    topup.payment_id = payment_id
    topup.status = TopUpStatus.PAID
    topup.paid_at = datetime.now(timezone.utc)
    advertiser.balance += topup.amount
    await db.commit()
    await db.refresh(advertiser)
    return _wallet(advertiser)


@router.post("/verify", response_model=AdvertiserTopUpVerifyOut)
async def verify_topup(
    payload: AdvertiserTopUpVerify,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser")),
) -> AdvertiserTopUpVerifyOut:
    topup = (
        await db.execute(
            select(AdvertiserTopUp).where(
                AdvertiserTopUp.order_id == payload.razorpay_order_id,
                AdvertiserTopUp.advertiser_id == user.advertiser_id,
            )
        )
    ).scalar_one_or_none()
    if topup is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Top-up order not found")
    _, key_secret = _credentials()
    expected = hmac.new(
        key_secret.encode(),
        f"{topup.order_id}|{payload.razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, payload.razorpay_signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment signature is invalid")

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{_RAZORPAY_API}/payments/{payload.razorpay_payment_id}",
                auth=httpx.BasicAuth(settings.razorpay_key_id or "", key_secret),
            )
            response.raise_for_status()
            payment = response.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Could not verify the Razorpay payment") from None

    if payment.get("order_id") != topup.order_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payment does not belong to this order")
    if payment.get("status") != "captured":
        raise HTTPException(status.HTTP_409_CONFLICT, "Payment has not been captured yet")
    wallet = await _credit_topup(
        db,
        order_id=topup.order_id,
        payment_id=payload.razorpay_payment_id,
        amount_paise=payment.get("amount", 0),
        currency=payment.get("currency", ""),
    )
    return AdvertiserTopUpVerifyOut(**wallet.model_dump(), status="paid")


@router.post("/razorpay/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    signature: str | None = Header(None, alias="X-Razorpay-Signature"),
) -> dict[str, str]:
    if settings.razorpay_webhook_secret is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Razorpay webhook is not configured")
    body = await request.body()
    expected = hmac.new(
        settings.razorpay_webhook_secret.get_secret_value().encode(), body, hashlib.sha256
    ).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook signature")
    try:
        event = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid webhook payload") from None

    if event.get("event") != "payment.captured":
        return {"status": "ignored"}
    try:
        payment = event["payload"]["payment"]["entity"]
        order_id = payment["order_id"]
        payment_id = payment["id"]
        amount_paise = payment["amount"]
        currency = payment["currency"]
    except (KeyError, TypeError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid captured-payment payload") from None

    topup_exists = await db.scalar(select(AdvertiserTopUp.id).where(AdvertiserTopUp.order_id == order_id))
    if topup_exists is None:
        return {"status": "ignored"}
    await _credit_topup(
        db,
        order_id=order_id,
        payment_id=payment_id,
        amount_paise=amount_paise,
        currency=currency,
    )
    return {"status": "credited"}
