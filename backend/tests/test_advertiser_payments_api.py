from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.api import advertiser_payments
from app.config import settings
from app.models.advertiser import AccountStatus
from app.models.payment import AdvertiserTopUp, TopUpStatus
from tests.conftest import auth_headers


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


@pytest.mark.asyncio
async def test_wallet_and_order_requires_active_advertiser_and_razorpay_config(client, db, advertiser_user, advertiser, monkeypatch):
    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    wallet = await client.get("/api/payments/wallet", headers=headers)
    assert wallet.status_code == 200 and wallet.json() == {"balance": "0.00", "credit_limit": "0.00", "currency": "INR"}
    assert (await client.post("/api/payments/orders", json={"amount": "100.00"}, headers=headers)).status_code == 403

    advertiser.status = AccountStatus.ACTIVE
    await db.commit()
    monkeypatch.setattr(settings, "razorpay_key_id", None)
    assert (await client.post("/api/payments/orders", json={"amount": "100.00"}, headers=headers)).status_code == 503


@pytest.mark.asyncio
async def test_order_creation_and_payment_verification_credit_wallet_once(client, db, advertiser_user, advertiser, monkeypatch):
    advertiser.status = AccountStatus.ACTIVE
    await db.commit()
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", type(settings.jwt_secret)("test-razorpay-secret"))
    headers = await auth_headers(client, "9123456789", "advertiserpass123")

    class OrderClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, **kwargs):
            assert url.endswith("/orders")
            assert kwargs["json"]["amount"] == 12550
            return FakeResponse({"id": "order_123456", "amount": 12550, "currency": "INR"})

    monkeypatch.setattr(advertiser_payments.httpx, "AsyncClient", OrderClient)
    order = await client.post("/api/payments/orders", json={"amount": "125.50"}, headers=headers)
    assert order.status_code == 200, order.text
    assert order.json()["order_id"] == "order_123456"
    assert await db.scalar(select(AdvertiserTopUp.status).where(AdvertiserTopUp.order_id == "order_123456")) == TopUpStatus.CREATED

    signature = hmac.new(b"test-razorpay-secret", b"order_123456|pay_123456", hashlib.sha256).hexdigest()
    class PaymentClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def get(self, url, **kwargs):
            assert url.endswith("/payments/pay_123456")
            return FakeResponse({"order_id": "order_123456", "amount": 12550, "currency": "INR", "status": "captured"})

    monkeypatch.setattr(advertiser_payments.httpx, "AsyncClient", PaymentClient)
    body = {"razorpay_order_id": "order_123456", "razorpay_payment_id": "pay_123456", "razorpay_signature": signature}
    verified = await client.post("/api/payments/verify", json=body, headers=headers)
    assert verified.status_code == 200, verified.text
    assert verified.json()["balance"] == "125.50"
    repeated = await client.post("/api/payments/verify", json=body, headers=headers)
    assert repeated.status_code == 200 and repeated.json()["balance"] == "125.50"
    topup = await db.scalar(select(AdvertiserTopUp).where(AdvertiserTopUp.order_id == "order_123456"))
    assert topup.status == TopUpStatus.PAID and topup.payment_id == "pay_123456"


@pytest.mark.asyncio
async def test_invalid_signature_and_amount_do_not_credit(client, db, advertiser_user, advertiser, monkeypatch):
    advertiser.status = AccountStatus.ACTIVE
    topup = AdvertiserTopUp(advertiser_id=advertiser.id, order_id="order_bad_123456", amount=Decimal("10.00"), status=TopUpStatus.CREATED)
    db.add(topup)
    await db.commit()
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_key")
    monkeypatch.setattr(settings, "razorpay_key_secret", type(settings.jwt_secret)("secret"))
    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    result = await client.post("/api/payments/verify", json={"razorpay_order_id": "order_bad_123456", "razorpay_payment_id": "pay_bad_123456", "razorpay_signature": "0" * 64}, headers=headers)
    assert result.status_code == 400
    assert advertiser.balance == Decimal("0.00")


@pytest.mark.asyncio
async def test_admin_can_list_topups_and_advertiser_cannot(client, db, admin_user, advertiser_user, advertiser):
    db.add(AdvertiserTopUp(advertiser_id=advertiser.id, order_id="listed", amount=Decimal("1.00"), status=TopUpStatus.CREATED))
    await db.commit()
    admin = await auth_headers(client, "9876543210", "adminpass123")
    advertiser_headers = await auth_headers(client, "9123456789", "advertiserpass123")
    rows = await client.get("/api/payments/topups", headers=admin)
    assert rows.status_code == 200 and rows.json()[0]["advertiser_name"] == advertiser.name
    assert (await client.get("/api/payments/topups", headers=advertiser_headers)).status_code == 403
