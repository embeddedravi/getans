from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy import select

from app.models.ad_unit import AdFormatType, AdUnit, AdUnitStatus
from app.models.advertiser import AccountStatus, Advertiser
from app.models.campaign import Campaign, CampaignStatus
from app.models.creative import Creative, CreativeFormat, ReviewStatus
from app.models.event import Event, EventType
from app.models.publisher import Publisher, PublisherStatus
from app.services.ad_selector import RequestContext, select_ad
from app.services.serve_token import issue_serve_token
from app.sockets.delivery_ns import DeliveryNamespace
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_create_poll_creative_valid(client, advertiser_user, advertiser, db):
    start = datetime.now(timezone.utc)
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Poll Campaign",
        status=CampaignStatus.ACTIVE,
        is_active=True,
        start_date=start,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    res = await client.post(
        "/api/creatives",
        json={
            "campaign_id": campaign.id,
            "name": "Tech Poll 1",
            "format": "poll",
            "poll_question": "What is your primary programming language?",
            "poll_options": ["Python", "TypeScript", "Go", "Rust"],
            "click_url": "https://advertiser.example.com/landing",
            "width": 300,
            "height": 250,
        },
        headers=headers,
    )
    assert res.status_code == 201
    data = res.json()
    assert data["format"] == "poll"
    assert data["width"] == 300
    assert data["height"] == 250
    assert data["custom_attributes"]["poll_question"] == "What is your primary programming language?"
    assert data["custom_attributes"]["poll_options"] == ["Python", "TypeScript", "Go", "Rust"]


@pytest.mark.asyncio
async def test_create_poll_creative_requires_four_options(client, advertiser_user, advertiser, db):
    start = datetime.now(timezone.utc)
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Invalid Poll Campaign",
        status=CampaignStatus.ACTIVE,
        is_active=True,
        start_date=start,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    # Only 3 options provided
    res = await client.post(
        "/api/creatives",
        json={
            "campaign_id": campaign.id,
            "format": "poll",
            "poll_question": "What is your favorite color?",
            "poll_options": ["Red", "Green", "Blue"],
            "click_url": "https://advertiser.example.com",
            "width": 300,
            "height": 250,
        },
        headers=headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_poll_creative_list_is_admin_wide_and_advertiser_scoped(client, advertiser_user, advertiser, admin_user, db):
    other_advertiser = Advertiser(name="Other Corp", billing_email="billing@other.example")
    db.add(other_advertiser)
    await db.commit()
    await db.refresh(other_advertiser)

    campaigns = []
    for owner, name in ((advertiser, "My campaign"), (other_advertiser, "Other campaign")):
        campaign = Campaign(
            advertiser_id=owner.id,
            name=name,
            status=CampaignStatus.ACTIVE,
            is_active=True,
            start_date=datetime.now(timezone.utc),
        )
        db.add(campaign)
        campaigns.append(campaign)
    await db.commit()
    for campaign in campaigns:
        await db.refresh(campaign)
        db.add(Creative(
            campaign_id=campaign.id,
            name=f"{campaign.name} poll",
            asset_url="https://poll.example.com/ad.png",
            click_url="https://advertiser.example.com/landing",
            format=CreativeFormat.POLL,
            width=300,
            height=250,
            custom_attributes={"poll_question": "Which option?", "poll_options": ["A", "B", "C", "D"]},
        ))
    await db.commit()

    advertiser_headers = await auth_headers(client, "9123456789", "advertiserpass123")
    admin_headers = await auth_headers(client, "9876543210", "adminpass123")
    advertiser_res = await client.get("/api/creatives/polls", headers=advertiser_headers)
    admin_res = await client.get("/api/creatives/polls", headers=admin_headers)

    assert advertiser_res.status_code == 200
    assert [row["campaign"]["name"] for row in advertiser_res.json()] == ["My campaign"]
    assert admin_res.status_code == 200
    assert {row["campaign"]["name"] for row in admin_res.json()} == {"My campaign", "Other campaign"}


@pytest.mark.asyncio
async def test_select_ad_matches_poll_ad_unit(db, publisher, advertiser):
    publisher.status = PublisherStatus.ACTIVE
    publisher.is_active = True
    advertiser.status = AccountStatus.ACTIVE
    advertiser.balance = Decimal("100.000000")
    await db.commit()

    poll_unit = AdUnit(
        publisher_id=publisher.id,
        slot_name="sidebar-poll",
        format_type=AdFormatType.POLL,
        width=300,
        height=250,
        status=AdUnitStatus.APPROVED,
        is_active=True,
    )
    db.add(poll_unit)

    now = datetime.now(timezone.utc)
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Poll Promotion",
        status=CampaignStatus.ACTIVE,
        is_active=True,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    poll_creative = Creative(
        campaign_id=campaign.id,
        name="Poll Creative",
        asset_url="https://poll.getans.local/ad.png",
        click_url="https://advertiser.example.com/promo",
        format=CreativeFormat.POLL,
        width=300,
        height=250,
        custom_attributes={
            "poll_question": "Which cloud provider do you use?",
            "poll_options": ["AWS", "Google Cloud", "Azure", "DigitalOcean"],
        },
        review_status=ReviewStatus.APPROVED,
        is_active=True,
    )
    campaign.creatives.append(poll_creative)
    db.add(poll_creative)
    await db.commit()

    selected = await select_ad(db, poll_unit.id, RequestContext())
    assert selected.creative_id == poll_creative.id
    assert selected.format == "poll"
    assert selected.custom_attributes["poll_question"] == "Which cloud provider do you use?"
    assert len(selected.custom_attributes["poll_options"]) == 4


@pytest.mark.asyncio
async def test_poll_vote_flow_and_results(client, admin_user, advertiser, publisher, db):
    publisher.status = PublisherStatus.ACTIVE
    publisher.is_active = True
    ad_unit = AdUnit(
        publisher_id=publisher.id,
        slot_name="poll-slot",
        format_type=AdFormatType.POLL,
        width=300,
        height=250,
        status=AdUnitStatus.APPROVED,
        is_active=True,
    )
    db.add(ad_unit)

    now = datetime.now(timezone.utc)
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name="Voting Campaign",
        status=CampaignStatus.ACTIVE,
        is_active=True,
        start_date=now - timedelta(days=1),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    creative = Creative(
        campaign_id=campaign.id,
        name="Voting Creative",
        asset_url="https://poll.getans.local/ad.png",
        click_url="https://advertiser.example.com/vote",
        format=CreativeFormat.POLL,
        width=300,
        height=250,
        custom_attributes={
            "poll_question": "Favorite database?",
            "poll_options": ["PostgreSQL", "MySQL", "SQLite", "MongoDB"],
        },
        review_status=ReviewStatus.APPROVED,
        is_active=True,
    )
    db.add(creative)
    await db.commit()
    await db.refresh(creative)

    # Issue serve token
    token, visitor = issue_serve_token(ad_unit.id, creative.id)

    delivery = DeliveryNamespace("/delivery")
    # Simulate client calling on_poll_vote
    res = await delivery.on_poll_vote(
        "mock-sid",
        {
            "ad_unit_id": ad_unit.id,
            "creative_id": creative.id,
            "visitor_id": visitor,
            "serve_token": token,
            "option_index": 1,  # MySQL
            "event_id": "pv-12345",
        },
    )
    assert res["ok"] is True
    assert res["selected_option"] == 1
    assert res["poll_results"]["counts"] == [0, 1, 0, 0]
    assert res["poll_results"]["percentages"] == [0.0, 100.0, 0.0, 0.0]
    assert res["poll_results"]["total_votes"] == 1

    # Check via REST API
    headers = await auth_headers(client, "9876543210", "adminpass123")
    api_res = await client.get(f"/api/creatives/{creative.id}/poll-results", headers=headers)
    assert api_res.status_code == 200
    stats = api_res.json()
    assert stats["creative_id"] == creative.id
    assert stats["question"] == "Favorite database?"
    assert stats["counts"] == [0, 1, 0, 0]
    assert stats["percentages"] == [0.0, 100.0, 0.0, 0.0]
    assert stats["total_votes"] == 1
