from __future__ import annotations

import pytest

from app.core.security import hash_password
from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.ad_report import AdReport
from app.models.advertiser import AccountStatus
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.event import Event, EventType
from app.models.publisher import PublisherStatus
from app.models.user import User
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_pending_approvals_and_review_lifecycle(client, db, admin_user, publisher, advertiser):
    unit = AdUnit(publisher_id=publisher.id, slot_name="pending", width=300, height=250)
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    admin = await auth_headers(client, "9876543210", "adminpass123")

    pending = await client.get("/api/admin/approvals/pending", headers=admin)
    assert pending.status_code == 200
    assert publisher.id in [row["id"] for row in pending.json()["publishers"]]
    assert advertiser.id in [row["id"] for row in pending.json()["advertisers"]]
    assert unit.id in [row["id"] for row in pending.json()["ad_units"]]

    pub_review = await client.patch(f"/api/admin/publishers/{publisher.id}/review", json={"status": "rejected", "rejection_reason": "  Invalid site  "}, headers=admin)
    assert pub_review.status_code == 200 and pub_review.json()["rejection_reason"] == "Invalid site"
    adv_review = await client.patch(f"/api/admin/advertisers/{advertiser.id}/review", json={"status": "active"}, headers=admin)
    assert adv_review.status_code == 200 and adv_review.json()["is_verified"] is True
    unit_review = await client.patch(f"/api/admin/ad-units/{unit.id}/review", json={"status": "approved"}, headers=admin)
    assert unit_review.status_code == 200 and unit_review.json()["is_active"] is True
    await db.refresh(unit)
    assert unit.report_review_round == 1
    assert (await client.patch(f"/api/admin/ad-units/{unit.id}/active", json={"is_active": False}, headers=admin)).json()["is_active"] is False
    assert (await client.get("/api/admin/approvals/pending", headers=admin)).json()["ad_units"] == []


@pytest.mark.asyncio
async def test_admin_user_controls_and_role_protection(client, db, admin_user, publisher):
    staff = User(mobile="+919811122333", role="staff", is_active=True, hashed_password="x")
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    admin = await auth_headers(client, "9876543210", "adminpass123")

    users = await client.get("/api/admin/users", headers=admin)
    assert users.status_code == 200 and len(users.json()) == 2
    changed = await client.patch(f"/api/admin/users/{staff.id}", json={"role": "publisher", "is_active": True, "publisher_id": publisher.id}, headers=admin)
    assert changed.status_code == 200 and changed.json()["publisher_id"] == publisher.id
    assert (await client.patch("/api/admin/users/9999", json={"role": "staff", "is_active": True}, headers=admin)).status_code == 404
    assert (await client.patch(f"/api/admin/users/{admin_user.id}", json={"role": "staff", "is_active": True}, headers=admin)).status_code == 400
    assert (await client.get("/api/admin/users")).status_code == 401


@pytest.mark.asyncio
async def test_admin_reports_are_scoped_to_current_review_round(client, db, admin_user, publisher, advertiser):
    unit = AdUnit(publisher_id=publisher.id, slot_name="reported", width=300, height=250, status=AdUnitStatus.PENDING_REVIEW)
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    db.add(AdReport(ad_unit_id=unit.id, creative_id=None, reporter_hash="a" * 64, review_round=0, reason="scam"))
    await db.commit()
    admin = await auth_headers(client, "9876543210", "adminpass123")

    reports = await client.get(f"/api/admin/ad-units/{unit.id}/reports", headers=admin)
    assert reports.status_code == 200 and len(reports.json()) == 1
    assert reports.json()[0]["reason"] == "scam"
    assert (await client.get("/api/admin/ad-units/9999/reports", headers=admin)).status_code == 404
    assert (await client.get(f"/api/admin/ad-units/{unit.id}/reports")).status_code == 401


@pytest.mark.asyncio
async def test_staff_can_review_but_cannot_use_admin_only_controls(client, db, publisher):
    staff = User(mobile="+919811122334", role="staff", is_active=True, hashed_password=hash_password("staffpass1"))
    db.add(staff)
    await db.commit()
    headers = await auth_headers(client, staff.mobile, "staffpass1")
    pending = await client.get("/api/admin/approvals/pending", headers=headers)
    assert pending.status_code == 200, pending.text
    review = await client.patch(f"/api/admin/publishers/{publisher.id}/review", json={"status": "active"}, headers=headers)
    assert review.status_code == 200
    assert (await client.get("/api/admin/users", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_admin_lists_advertisers_and_recent_events_with_cursor(client, db, admin_user, publisher, advertiser):
    from datetime import datetime, timedelta, timezone

    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Recent campaign",
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(campaign)
    unit = AdUnit(publisher_id=publisher.id, slot_name="recent", width=300, height=250)
    db.add(unit)
    await db.commit()
    creative = Creative(campaign_id=campaign.id, asset_url="https://cdn.example/a.png", click_url="https://click.example", width=300, height=250)
    db.add(creative)
    await db.commit()
    event = Event(ad_unit_id=unit.id, campaign_id=campaign.id, creative_id=creative.id, type=EventType.CLICK, cost=0, is_valid=True, country_code="CA")
    db.add(event)
    await db.commit()
    await db.refresh(event)
    admin = await auth_headers(client, "9876543210", "adminpass123")

    advertisers = await client.get("/api/admin/advertisers", headers=admin)
    assert advertisers.status_code == 200 and advertisers.json()[0]["id"] == advertiser.id
    rows = await client.get("/api/admin/events/recent", headers=admin)
    assert rows.status_code == 200 and rows.json()[0]["campaign_name"] == "Recent campaign"
    assert rows.json()[0]["slot_name"] == "recent" and rows.json()[0]["country_code"] == "CA"
    assert (await client.get(f"/api/admin/events/recent?after_id={event.id}", headers=admin)).json() == []
    assert (await client.get("/api/admin/events/recent", headers=admin, params={"limit": 0})).status_code == 422
