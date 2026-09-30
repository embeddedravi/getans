from __future__ import annotations

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.advertiser import Advertiser
from app.models.publisher import Publisher, PublisherStatus
from app.models.user import User
from tests.conftest import auth_headers

PW = "supersecret1"


def advertiser_body(**over):
    return {"mobile": "98111 22333", "password": PW, "role": "advertiser",
            "organization_name": "Acme Ads", "billing_email": "billing@acme.example", **over}


def publisher_body(**over):
    return {"mobile": "9822233344", "password": PW, "role": "publisher",
            "organization_name": "Daily News", "site_url": "https://news.example.com",
            "payout_email": "pay@news.example.com", **over}


@pytest.mark.asyncio
async def test_advertiser_signup_creates_linked_tenant(client, db):
    res = await client.post("/api/auth/signup", json=advertiser_body())
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["mobile"] == "+919811122333"
    assert body["role"] == "advertiser"
    assert body["is_verified"] is False

    adv = (await db.execute(select(Advertiser).where(Advertiser.name == "Acme Ads"))).scalar_one()
    assert body["advertiser_id"] == adv.id and body["publisher_id"] is None


@pytest.mark.asyncio
async def test_publisher_signup_starts_pending_with_api_key(client, db):
    res = await client.post("/api/auth/signup", json=publisher_body())
    assert res.status_code == 201, res.text
    pub = (await db.execute(select(Publisher).where(Publisher.name == "Daily News"))).scalar_one()
    assert pub.status == PublisherStatus.PENDING_APPROVAL
    assert pub.api_key.startswith("pub_live_")
    assert res.json()["publisher_id"] == pub.id


@pytest.mark.asyncio
async def test_can_log_in_after_signup(client):
    await client.post("/api/auth/signup", json=advertiser_body())
    headers = await auth_headers(client, "9811122333", PW)
    me = await client.get("/api/auth/me", headers=headers)
    assert me.json()["role"] == "advertiser"


@pytest.mark.asyncio
async def test_admin_role_cannot_be_requested(client):
    res = await client.post("/api/auth/signup", json=advertiser_body(role="admin"))
    assert res.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["site_url", "payout_email"])
async def test_publisher_requires_site_and_payout_email(client, missing):
    body = publisher_body()
    body.pop(missing)
    assert (await client.post("/api/auth/signup", json=body)).status_code == 422


@pytest.mark.asyncio
async def test_advertiser_needs_some_email(client):
    body = advertiser_body()
    body.pop("billing_email")
    assert (await client.post("/api/auth/signup", json=body)).status_code == 422
    body["email"] = "me@acme.example"  # falls back to email
    assert (await client.post("/api/auth/signup", json=body)).status_code == 201


@pytest.mark.asyncio
async def test_duplicate_mobile_conflicts_without_creating_tenant(client, db):
    assert (await client.post("/api/auth/signup", json=advertiser_body())).status_code == 201
    res = await client.post("/api/auth/signup", json=advertiser_body(organization_name="Second"))
    assert res.status_code == 409
    assert (await db.execute(select(Advertiser).where(Advertiser.name == "Second"))).first() is None
    assert len((await db.execute(select(User))).scalars().all()) == 1


@pytest.mark.asyncio
async def test_invalid_mobile_and_short_password_rejected(client):
    assert (await client.post("/api/auth/signup", json=advertiser_body(mobile="12345"))).status_code == 422
    assert (await client.post("/api/auth/signup", json=advertiser_body(password="short"))).status_code == 422


@pytest.mark.asyncio
async def test_signup_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_self_signup", False)
    assert (await client.post("/api/auth/signup", json=advertiser_body())).status_code == 404