from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative, ReviewStatus
from app.models.event import Event, EventType
from app.models.publisher import Publisher
from app.models.user import User
from tests.conftest import auth_headers, campaign_window


@pytest_asyncio.fixture
async def publisher_user(db, publisher):
    user = User(
        mobile="+919811122333",
        hashed_password=hash_password("publisherpass1"),
        role="publisher",
        publisher_id=publisher.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    return user


async def make_campaign(db, advertiser, name="Campaign"):
    start, end = campaign_window()
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name=name,
        start_date=datetime.fromisoformat(start),
        end_date=datetime.fromisoformat(end),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def make_creative(db, campaign):
    creative = Creative(
        campaign_id=campaign.id,
        name="Banner",
        asset_url="https://cdn.example.com/ad.png",
        click_url="https://advertiser.example.com",
        width=300,
        height=250,
    )
    db.add(creative)
    await db.commit()
    await db.refresh(creative)
    return creative


@pytest.mark.asyncio
async def test_publishers_admin_crud_and_publisher_scope(client, admin_user, publisher_user, publisher):
    admin = await auth_headers(client, "9876543210", "adminpass123")
    pub_headers = await auth_headers(client, "9811122333", "publisherpass1")

    created = await client.post(
        "/api/publishers",
        json={"name": "New Publisher", "site_url": "https://new.example.com", "payout_email": "pay@new.example.com"},
        headers=admin,
    )
    assert created.status_code == 201, created.text
    assert created.json()["api_key"].startswith("pub_live_")

    assert (await client.post("/api/publishers", json={"name": "No", "site_url": "https://x.example", "payout_email": "x@example.com"})).status_code == 401
    listed = await client.get("/api/publishers", headers=pub_headers)
    assert [row["id"] for row in listed.json()] == [publisher.id]
    assert (await client.get("/api/publishers/9999", headers=pub_headers)).status_code == 403
    assert (await client.get(f"/api/publishers/{publisher.id}", headers=pub_headers)).status_code == 200


@pytest.mark.asyncio
async def test_ad_unit_create_and_access_rules(client, admin_user, publisher_user, publisher):
    admin = await auth_headers(client, "9876543210", "adminpass123")
    pub_headers = await auth_headers(client, "9811122333", "publisherpass1")
    payload = {"publisher_id": publisher.id, "slot_name": "sidebar", "width": 300, "height": 250}

    created = await client.post(f"/api/publishers/{publisher.id}/ad-units", json=payload, headers=pub_headers)
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "pending_review"
    assert (await client.post(f"/api/publishers/{publisher.id}/ad-units", json={**payload, "publisher_id": 999}, headers=admin)).status_code == 400
    assert (await client.get(f"/api/publishers/{publisher.id}/ad-units", headers=pub_headers)).json()[0]["slot_name"] == "sidebar"
    assert (await client.get("/api/publishers/9999/ad-units", headers=pub_headers)).status_code == 403
    assert (await client.post("/api/publishers/9999/ad-units", json={**payload, "publisher_id": 9999}, headers=pub_headers)).status_code == 403


@pytest.mark.asyncio
async def test_creative_create_update_review_and_delete_with_tenant_scope(client, db, advertiser, advertiser_user, admin_user):
    other = type(advertiser)(name="Other", billing_email="other@example.com")
    db.add(other)
    await db.commit()
    own = await make_campaign(db, advertiser, "Own")
    foreign = await make_campaign(db, other, "Foreign")
    adv_headers = await auth_headers(client, "9123456789", "advertiserpass123")
    admin_headers = await auth_headers(client, "9876543210", "adminpass123")
    body = {"campaign_id": own.id, "name": "First", "asset_url": "https://cdn.example.com/a.png", "click_url": "https://example.com", "width": 300, "height": 250}

    created = await client.post("/api/creatives", json=body, headers=adv_headers)
    assert created.status_code == 201, created.text
    creative_id = created.json()["id"]
    assert (await client.post("/api/creatives", json={**body, "campaign_id": foreign.id}, headers=adv_headers)).status_code == 403
    assert (await client.post("/api/creatives", json={**body, "campaign_id": 9999}, headers=admin_headers)).status_code == 404
    assert len((await client.get(f"/api/creatives/by-campaign/{own.id}", headers=adv_headers)).json()) == 1
    assert (await client.get(f"/api/creatives/by-campaign/{foreign.id}", headers=adv_headers)).status_code == 403

    updated = await client.patch(f"/api/creatives/{creative_id}", json={"name": "Updated", "is_active": False}, headers=adv_headers)
    assert updated.status_code == 200 and updated.json()["name"] == "Updated"
    reviewed = await client.patch(f"/api/creatives/{creative_id}/review", json={"review_status": "rejected", "rejection_reason": "Bad landing page"}, headers=admin_headers)
    assert reviewed.status_code == 200 and reviewed.json()["review_status"] == "rejected"
    assert (await client.patch(f"/api/creatives/{creative_id}/review", json={"review_status": "approved"}, headers=adv_headers)).status_code == 403
    assert (await client.delete(f"/api/creatives/{creative_id}", headers=adv_headers)).status_code == 204
    assert (await client.delete(f"/api/creatives/{creative_id}", headers=admin_headers)).status_code == 404


@pytest.mark.asyncio
async def test_campaign_analytics_aggregates_range_and_scopes_advertiser(client, db, advertiser, advertiser_user, admin_user, publisher):
    other = type(advertiser)(name="Other", billing_email="other@example.com")
    db.add(other)
    await db.commit()
    own = await make_campaign(db, advertiser, "Own")
    foreign = await make_campaign(db, other, "Foreign")
    unit = AdUnit(publisher_id=publisher.id, slot_name="analytics", width=300, height=250)
    db.add(unit)
    await db.commit()
    own_creative = await make_creative(db, own)
    foreign_creative = await make_creative(db, foreign)
    now = datetime.now(timezone.utc)
    for campaign, creative, event_type in [(own, own_creative, EventType.IMPRESSION), (own, own_creative, EventType.IMPRESSION), (own, own_creative, EventType.CLICK), (foreign, foreign_creative, EventType.IMPRESSION)]:
        db.add(Event(campaign_id=campaign.id, ad_unit_id=unit.id, creative_id=creative.id, type=event_type, timestamp=now, cost=0, is_valid=True))
    await db.commit()
    start = (now - timedelta(days=1)).isoformat()
    end = (now + timedelta(days=1)).isoformat()
    adv_headers = await auth_headers(client, "9123456789", "advertiserpass123")
    admin_headers = await auth_headers(client, "9876543210", "adminpass123")

    params = {"start": start, "end": end}
    result = await client.get("/api/analytics/campaigns", params=params, headers=adv_headers)
    assert result.status_code == 200, result.text
    assert result.json() == [{"campaign_id": own.id, "campaign_name": "Own", "impressions": 2, "clicks": 1, "ctr": 50.0}]
    all_rows = await client.get("/api/analytics/campaigns", params=params, headers=admin_headers)
    assert len(all_rows.json()) == 2
    assert (await client.get("/api/analytics/campaigns", params=params)).status_code == 401
