from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.api import delivery
from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative, ReviewStatus


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

    monkeypatch.setattr(delivery, "authenticate_publisher", authenticate)
    monkeypatch.setattr(delivery, "record_event", record_event)

    response = await client.post(
        "/api/delivery/events/conversion",
        headers={"X-Publisher-Key": publisher.api_key},
        json={
            "ad_unit_id": unit.id,
            "creative_id": creative.id,
            "event_id": "conversion-event-1",
            "visitor_id": "visitor-1",
        },
    )

    assert response.status_code == 204
    assert seen[0]["event_type"] == "conversion"
    assert seen[0]["creative_id"] == creative.id
