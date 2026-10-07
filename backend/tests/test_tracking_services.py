from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.event import Event, EventType
from app.models.publisher import PublisherStatus
from app.services import budget_tracker, publisher_auth, sms
from app.schemas.event import EventIngest, EventOut
from tests.conftest import campaign_window


@pytest.mark.asyncio
async def test_record_event_stores_metadata_emits_updates_and_deduplicates(db, advertiser, publisher, monkeypatch):
    publisher.status = PublisherStatus.ACTIVE
    await db.commit()
    start, end = campaign_window()
    campaign = Campaign(advertiser_id=advertiser.id, name="Tracking", start_date=datetime.fromisoformat(start), end_date=datetime.fromisoformat(end))
    db.add(campaign)
    await db.commit()
    unit = AdUnit(publisher_id=publisher.id, slot_name="tracking", width=300, height=250)
    db.add(unit)
    await db.commit()
    creative = Creative(campaign_id=campaign.id, asset_url="https://cdn.example/ad.png", click_url="https://click.example", width=300, height=250)
    db.add(creative)
    await db.commit()

    spend = []
    updates = []
    live = []
    monkeypatch.setattr(budget_tracker, "record_spend", lambda campaign_id, cost: spend.append((campaign_id, cost)))
    async def update(*args, **kwargs): updates.append((args, kwargs))
    async def live_event(payload): live.append(payload)
    monkeypatch.setattr(budget_tracker, "_emit_dashboard_update", update)
    monkeypatch.setattr(budget_tracker, "_emit_live_event", live_event)

    await budget_tracker.record_event("impression", unit.id, creative.id, user_ip="192.0.2.4", user_agent="agent", country_code="US", visitor_id="anon-visitor")
    await budget_tracker.record_event(EventType.IMPRESSION, unit.id, creative.id, visitor_id="anon-visitor")
    rows = (await db.execute(select(Event))).scalars().all()
    assert len(rows) == 1
    assert rows[0].cost == budget_tracker._COST_PER_EVENT[EventType.IMPRESSION]
    assert rows[0].country_code == "US" and rows[0].user_ip == "192.0.2.4"
    assert len(spend) == len(updates) == len(live) == 1
    assert live[0]["campaign_name"] == "Tracking" and live[0]["slot_name"] == "tracking"


@pytest.mark.asyncio
async def test_record_event_validates_type_and_creative(db):
    with pytest.raises(ValueError, match="Unknown event type"):
        await budget_tracker.record_event("bogus", 1, 1)
    with pytest.raises(ValueError, match="Unsupported tracking cost type"):
        await budget_tracker.record_event(EventType.VIEWABLE_IMPRESSION, 1, 1)
    with pytest.raises(ValueError, match="Unknown creative_id"):
        await budget_tracker.record_event("click", 1, 999)


@pytest.mark.asyncio
async def test_publishers_authentication_requires_active_approved_account(db, publisher):
    assert await publisher_auth.authenticate_publisher(publisher.api_key) is None
    publisher.status = PublisherStatus.ACTIVE
    publisher.is_active = True
    await db.commit()
    assert (await publisher_auth.authenticate_publisher(publisher.api_key)).id == publisher.id
    assert await publisher_auth.authenticate_publisher("") is None


@pytest.mark.asyncio
async def test_console_sms_and_unimplemented_provider(monkeypatch, caplog):
    monkeypatch.setattr(settings, "sms_backend", "console")
    await sms.send_sms("+919876543210", "OTP 123456")
    assert "OTP 123456" in caplog.text
    monkeypatch.setattr(settings, "sms_backend", "twilio")
    with pytest.raises(NotImplementedError, match="twilio"):
        await sms.send_sms("+919876543210", "OTP 123456")


def test_event_schemas_validate_cost_and_round_trip_event():
    payload = EventIngest(ad_unit_id=1, campaign_id=2, creative_id=3, type="click", meta={"source": "web"})
    assert payload.cost == 0 and payload.meta == {"source": "web"}
    with pytest.raises(ValueError):
        EventIngest(ad_unit_id=1, campaign_id=2, creative_id=3, type="click", cost="-0.01")

    now = datetime.now(timezone.utc)
    event = EventOut(
        id=4, event_id=None, ad_unit_id=1, campaign_id=2, creative_id=3,
        type="impression", timestamp=now, cost="0.001000", is_valid=True,
        country_code="US", meta={"source": "socket"},
    )
    assert event.type.value == "impression" and event.country_code == "US"
