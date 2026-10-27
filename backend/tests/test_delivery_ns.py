from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.sockets import delivery_ns
from app.sockets.delivery_ns import DeliveryNamespace, _normalize_country
from tests.conftest import campaign_window


@pytest.fixture
def namespace(monkeypatch):
    ns = DeliveryNamespace("/delivery")
    ns.emitted = []

    async def emit(event, data, to=None):
        ns.emitted.append((event, data, to))

    ns.emit = emit
    return ns


@pytest.mark.asyncio
async def test_request_ad_rejects_missing_and_unknown_publisher(namespace, monkeypatch):
    async def should_not_auth(_key):
        raise AssertionError("missing request parameters must fail before authentication")

    monkeypatch.setattr(delivery_ns, "authenticate_publisher", should_not_auth)
    await namespace.on_request_ad("sid", {})
    assert namespace.emitted[-1] == ("no_fill", {"reason": "missing_params"}, "sid")

    async def unknown(_key): return None
    monkeypatch.setattr(delivery_ns, "authenticate_publisher", unknown)
    await namespace.on_request_ad("sid", {"ad_unit_id": 3, "api_key": "bad"})
    assert namespace.emitted[-1] == ("no_fill", {"reason": "unauthorized"}, "sid")


@pytest.mark.asyncio
async def test_request_ad_persists_normalized_context_and_serves_creative(namespace, publisher, monkeypatch):
    saved = {}
    async def authenticate(_key): return publisher
    async def get_session(_sid): return {}
    async def save_session(_sid, session): saved.update(session)
    async def select(_db, ad_unit_id, context):
        assert ad_unit_id == 42
        assert context.country is None and context.device_type == "mobile"
        return SimpleNamespace(
            campaign_id=5, creative_id=8,
            asset_url="https://cdn.example/ad.png", click_url="https://click.example",
            width=300, height=250, format="image",
            custom_attributes=None, html_snippet=None,
        )

    class FakeResult:
        def scalar_one_or_none(self): return 42
    class FakeDb:
        async def scalar(self, *a, **kw): return 42  # ad_unit exists
        async def execute(self, *a, **kw): return FakeResult()
    async def db_generator():
        yield FakeDb()

    namespace.get_session = get_session
    namespace.save_session = save_session
    monkeypatch.setattr(delivery_ns, "authenticate_publisher", authenticate)
    monkeypatch.setattr(delivery_ns, "get_session", db_generator)
    monkeypatch.setattr(delivery_ns, "select_ad", select)
    await namespace.on_request_ad("sid", {"ad_unit_id": 42, "api_key": "valid", "context": {"country": "ca", "device_type": "mobile"}})
    assert saved["country_code"] is None  # no environ in test, country header absent
    event, payload, to = namespace.emitted[-1]
    assert event == "serve_ad" and to == "sid"
    assert payload["campaign_id"] == 5
    assert payload["asset_url"] == "https://cdn.example/ad.png"
    assert payload["format"] == "image"
    assert "serve_token" in payload


@pytest.mark.asyncio
async def test_impression_and_click_forward_metadata(namespace, monkeypatch):
    seen = []
    async def metadata(_sid, data):
        return {"user_ip": "192.0.2.1", "user_agent": "test-agent", "country_code": "CA"}
    async def record_event(**kwargs): seen.append(kwargs)
    def fake_verify(token, ad_unit_id, creative_id): return "visitor-abc"
    namespace._event_metadata = metadata
    monkeypatch.setattr(delivery_ns, "record_event", record_event)
    monkeypatch.setattr(delivery_ns, "verify_serve_token", fake_verify)

    await namespace.on_impression("sid", {"ad_unit_id": 1, "creative_id": 2, "event_id": "evt1", "serve_token": "tok", "country_code": "CA"})
    await namespace.on_click("sid", {"ad_unit_id": 1, "creative_id": 2, "event_id": "evt2", "serve_token": "tok", "country_code": "CA"})
    assert [event["event_type"] for event in seen] == ["impression", "click"]
    assert all(event["user_ip"] == "192.0.2.1" and event["country_code"] == "CA" for event in seen)


@pytest.mark.asyncio
async def test_reports_deduplicate_visitors_and_pause_slot_at_threshold(namespace, db, publisher, monkeypatch):
    unit = AdUnit(publisher_id=publisher.id, slot_name="review", width=300, height=250, status=AdUnitStatus.APPROVED)
    db.add(unit)
    await db.commit()
    start, end = campaign_window()
    from app.models.advertiser import Advertiser
    advertiser = Advertiser(name="Acme", billing_email="billing@example.com")
    db.add(advertiser)
    await db.commit()
    campaign = Campaign(advertiser_id=advertiser.id, name="Review ad", start_date=datetime.fromisoformat(start), end_date=datetime.fromisoformat(end))
    db.add(campaign)
    await db.commit()
    from app.models.creative import ReviewStatus
    creative = Creative(campaign_id=campaign.id, asset_url="https://cdn.example/ad.png", click_url="https://click.example", width=300, height=250, review_status=ReviewStatus.APPROVED, is_active=True)
    db.add(creative)
    await db.commit()
    await db.refresh(unit)

    async def authenticate(_key): return publisher
    async def db_generator(): yield db
    # Stub verify_serve_token to return the visitor_id directly so we don't need real tokens
    def fake_verify(token, ad_unit_id, creative_id): return token  # token IS the visitor_id in test
    monkeypatch.setattr(delivery_ns, "authenticate_publisher", authenticate)
    monkeypatch.setattr(delivery_ns, "get_session", db_generator)
    monkeypatch.setattr(delivery_ns, "verify_serve_token", fake_verify)

    def make_data(unit_id, visitor, reason):
        return {"api_key": "valid", "ad_unit_id": unit_id, "creative_id": creative.id,
                "visitor_id": visitor, "serve_token": visitor, "reason": reason}

    invalid = await namespace.on_report_ad("sid", {"api_key": "valid", "ad_unit_id": "bad", "creative_id": creative.id, "visitor_id": "visitor-identifier-0001", "serve_token": "visitor-identifier-0001", "reason": "scam"})
    assert invalid["ok"] is False
    one = await namespace.on_report_ad("sid", make_data(unit.id, "visitor-identifier-0001", "scam"))
    duplicate = await namespace.on_report_ad("sid", make_data(unit.id, "visitor-identifier-0001", "scam"))
    two = await namespace.on_report_ad("sid", make_data(unit.id, "visitor-identifier-0002", "adult_content"))
    three = await namespace.on_report_ad("sid", make_data(unit.id, "visitor-identifier-0003", "other"))
    assert one["report_count"] == 1 and duplicate["duplicate"] is True
    assert two["pending_review"] is False and three["pending_review"] is True
    await db.refresh(unit)
    assert unit.status == AdUnitStatus.PENDING_REVIEW and unit.is_active is False


@pytest.mark.parametrize("value,expected", [(" us ", "US"), ("CA", "CA"), ("USA", None), ("1A", None), (None, None), (1, None)])
def test_country_header_normalization(value, expected):
    assert _normalize_country(value) == expected
