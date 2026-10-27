from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.api import delivery
from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative, ReviewStatus
from app.services import serve_token as serve_token_module


@pytest.mark.asyncio
async def test_conversion_events_are_accepted_for_cpa_billing(client, db, advertiser, publisher, monkeypatch):
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Conversion campaign",
        start_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db.add(campaign)
    await db.commit()
    unit = AdUnit(publisher_id=publisher.id, slot_name="conversion-slot", width=300, height=250)
    db.add(unit)
    await db.commit()
    creative = Creative(
        campaign_id=campaign.id,
        asset_url="https://cdn.example/ad.png",
        click_url="https://advertiser.example/landing",
        width=300,
        height=250,
        review_status=ReviewStatus.APPROVED,
    )
    db.add(creative)
    await db.commit()

    async def authenticate(_key):
        return publisher

    seen = []

    async def record_event(**kwargs):
        seen.append(kwargs)

    # Stub verify_serve_token so we don't need a real token, and return a long-enough visitor_id
    FAKE_VISITOR = "visitor-1-padded-to-16chars"
    def fake_verify(token, ad_unit_id, creative_id): return FAKE_VISITOR

    monkeypatch.setattr(delivery, "authenticate_publisher", authenticate)
    monkeypatch.setattr(delivery, "record_event", record_event)
    monkeypatch.setattr(delivery, "verify_serve_token", fake_verify)

    response = await client.post(
        "/api/delivery/events/conversion",
        headers={"X-Publisher-Key": publisher.api_key},
        json={
            "ad_unit_id": unit.id,
            "creative_id": creative.id,
            "event_id": "conversion-event-1",
            "visitor_id": FAKE_VISITOR,
            "serve_token": "a" * 20,  # min_length=20 required by schema
        },
    )

    assert response.status_code == 204
    assert seen[0]["event_type"] == "conversion"
    assert seen[0]["creative_id"] == creative.id
