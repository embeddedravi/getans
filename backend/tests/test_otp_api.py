from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update

from app.config import settings
from app.models.otp import OTPCode

MOBILE = "9876543210"


@pytest.fixture
def sms(monkeypatch):
    sent: list[tuple[str, str]] = []

    async def fake_send(mobile: str, message: str) -> None:
        sent.append((mobile, message))

    monkeypatch.setattr("app.api.otp.send_sms", fake_send)
    return sent


def _code(sms) -> str:
    return re.search(r"\b(\d{6})\b", sms[-1][1]).group(1)


@pytest.fixture(autouse=True)
def _no_cooldown(monkeypatch):
    monkeypatch.setattr(settings, "otp_resend_cooldown_seconds", 0)


@pytest.mark.asyncio
async def test_request_and_verify_marks_user_verified(client, admin_user, db, sms):
    assert admin_user.is_verified is False

    res = await client.post("/api/auth/otp/request", json={"mobile": MOBILE})
    assert res.status_code == 202
    assert sms[0][0] == "+919876543210"

    res = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": _code(sms)})
    assert res.status_code == 200, res.text

    await db.refresh(admin_user)
    assert admin_user.is_verified is True


@pytest.mark.asyncio
async def test_unknown_mobile_gets_same_response_and_no_sms(client, sms):
    res = await client.post("/api/auth/otp/request", json={"mobile": "9000000000"})
    assert res.status_code == 202
    assert sms == []


@pytest.mark.asyncio
async def test_wrong_code_rejected_then_locked_after_max_attempts(client, admin_user, sms):
    await client.post("/api/auth/otp/request", json={"mobile": MOBILE})
    real = _code(sms)
    wrong = "000000" if real != "000000" else "111111"

    for _ in range(settings.otp_max_attempts):
        res = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": wrong})
        assert res.status_code == 400

    # Even the correct code no longer works once attempts are exhausted.
    res = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": real})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_expired_code_rejected(client, admin_user, db, sms):
    await client.post("/api/auth/otp/request", json={"mobile": MOBILE})
    await db.execute(update(OTPCode).values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    await db.commit()

    res = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": _code(sms)})
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_code_is_single_use_and_new_code_invalidates_old(client, admin_user, sms):
    await client.post("/api/auth/otp/request", json={"mobile": MOBILE})
    first = _code(sms)
    await client.post("/api/auth/otp/request", json={"mobile": MOBILE})
    second = _code(sms)

    if first != second:
        res = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": first})
        assert res.status_code == 400

    ok = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": second})
    assert ok.status_code == 200
    again = await client.post("/api/auth/otp/verify", json={"mobile": MOBILE, "code": second})
    assert again.status_code == 400


@pytest.mark.asyncio
async def test_resend_cooldown_returns_429(client, admin_user, sms, monkeypatch):
    monkeypatch.setattr(settings, "otp_resend_cooldown_seconds", 60)
    assert (await client.post("/api/auth/otp/request", json={"mobile": MOBILE})).status_code == 202
    res = await client.post("/api/auth/otp/request", json={"mobile": MOBILE})
    assert res.status_code == 429
    assert "retry-after" in res.headers


@pytest.mark.asyncio
async def test_hourly_cap_returns_429(client, admin_user, sms, monkeypatch):
    monkeypatch.setattr(settings, "otp_max_per_hour", 2)
    for _ in range(2):
        assert (await client.post("/api/auth/otp/request", json={"mobile": MOBILE})).status_code == 202
    assert (await client.post("/api/auth/otp/request", json={"mobile": MOBILE})).status_code == 429


@pytest.mark.asyncio
async def test_login_blocked_for_unverified_when_required(client, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "require_verified_mobile", True)
    res = await client.post("/api/auth/login", json={"mobile": MOBILE, "password": "adminpass123"})
    assert res.status_code == 403
