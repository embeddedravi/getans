from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.services.ad_selector import NoEligibleCampaignError, RequestContext, select_ad


async def _make_ad_unit(db, publisher, width=300, height=250) -> AdUnit:
    unit = AdUnit(publisher_id=publisher.id, slot_name="test-slot", width=width, height=height)
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    return unit


async def _make_campaign(
    db,
    advertiser,
    *,
    priority=1,
    daily_cap=None,
    targeting_rules=None,
    is_active=True,
    width=300,
    height=250,
) -> Campaign:
    now = datetime.now(timezone.utc)
    campaign = Campaign(
        advertiser_id=advertiser.id,
        name=f"Campaign p{priority}",
        is_active=is_active,
        priority=priority,
        daily_cap=daily_cap,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
        targeting_rules=targeting_rules,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)

    creative = Creative(
        campaign_id=campaign.id,
        asset_url="https://cdn.example.com/ad.png",
        click_url="https://advertiser.example.com",
        width=width,
        height=height,
    )
    db.add(creative)
    await db.commit()

    return campaign


@pytest.mark.asyncio
async def test_no_campaigns_raises(db, publisher):
    ad_unit = await _make_ad_unit(db, publisher)

    with pytest.raises(NoEligibleCampaignError):
        await select_ad(db, ad_unit.id)


@pytest.mark.asyncio
async def test_selects_matching_campaign(db, publisher, advertiser):
    ad_unit = await _make_ad_unit(db, publisher)
    await _make_campaign(db, advertiser)

    result = await select_ad(db, ad_unit.id)

    assert result.asset_url == "https://cdn.example.com/ad.png"


@pytest.mark.asyncio
async def test_dimension_mismatch_excludes_campaign(db, publisher, advertiser):
    ad_unit = await _make_ad_unit(db, publisher, width=728, height=90)
    await _make_campaign(db, advertiser, width=300, height=250)

    with pytest.raises(NoEligibleCampaignError):
        await select_ad(db, ad_unit.id)


@pytest.mark.asyncio
async def test_inactive_campaign_excluded(db, publisher, advertiser):
    ad_unit = await _make_ad_unit(db, publisher)
    await _make_campaign(db, advertiser, is_active=False)

    with pytest.raises(NoEligibleCampaignError):
        await select_ad(db, ad_unit.id)


@pytest.mark.asyncio
async def test_targeting_country_mismatch_excludes_campaign(db, publisher, advertiser):
    ad_unit = await _make_ad_unit(db, publisher)
    await _make_campaign(db, advertiser, targeting_rules={"countries": ["US"]})

    with pytest.raises(NoEligibleCampaignError):
        await select_ad(db, ad_unit.id, RequestContext(country="FR"))


@pytest.mark.asyncio
async def test_targeting_country_match_selects_campaign(db, publisher, advertiser):
    ad_unit = await _make_ad_unit(db, publisher)
    await _make_campaign(db, advertiser, targeting_rules={"countries": ["US", "CA"]})

    result = await select_ad(db, ad_unit.id, RequestContext(country="CA"))

    assert result.campaign_id is not None


@pytest.mark.asyncio
async def test_higher_priority_campaign_wins(db, publisher, advertiser):
    ad_unit = await _make_ad_unit(db, publisher)
    low = await _make_campaign(db, advertiser, priority=1)
    high = await _make_campaign(db, advertiser, priority=10)

    # Run several times since ties within a priority tier are randomized --
    # the higher-priority campaign should win every time regardless.
    for _ in range(10):
        result = await select_ad(db, ad_unit.id)
        assert result.campaign_id == high.id
        assert result.campaign_id != low.id


@pytest.mark.asyncio
async def test_daily_cap_exhausted_excludes_campaign(db, publisher, advertiser, fake_redis):
    ad_unit = await _make_ad_unit(db, publisher)
    campaign = await _make_campaign(db, advertiser, daily_cap=1.0)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await fake_redis.set(f"campaign:{campaign.id}:spend:{today}", "1.50")

    with pytest.raises(NoEligibleCampaignError):
        await select_ad(db, ad_unit.id)


@pytest.mark.asyncio
async def test_daily_cap_with_remaining_budget_selects_campaign(
    db, publisher, advertiser, fake_redis
):
    ad_unit = await _make_ad_unit(db, publisher)
    campaign = await _make_campaign(db, advertiser, daily_cap=10.0)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    await fake_redis.set(f"campaign:{campaign.id}:spend:{today}", "2.00")

    result = await select_ad(db, ad_unit.id)

    assert result.campaign_id == campaign.id
