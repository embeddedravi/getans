"""
Ad selection service.

Given an ad unit (a slot on a publisher's page) and optional request context
(geo, device, page keywords, etc.), select the best eligible campaign's
creative to serve.

Selection order:
    1. Filter to campaigns that are active, within date range, and match
       the ad unit's dimensions.
    2. Filter to campaigns that pass targeting rules against the request context.
    3. Filter to campaigns with remaining budget (checked against Redis, the
       fast-path budget counter -- not Postgres, to avoid a DB hit on every
       ad request).
    4. Rank remaining campaigns by priority, then by a small random factor
       to avoid one campaign always winning ties.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client
from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative


@dataclass
class RequestContext:
    """Signals passed along with an ad request, used for targeting."""

    country: str | None = None
    device_type: str | None = None  # "desktop" | "mobile" | "tablet"
    page_keywords: list[str] | None = None


@dataclass
class SelectedAd:
    campaign_id: int
    creative_id: int
    asset_url: str
    click_url: str
    width: int
    height: int


class NoEligibleCampaignError(Exception):
    """Raised when no campaign can be served for a given ad unit/context."""


async def select_ad(
    db: AsyncSession,
    ad_unit_id: int,
    context: RequestContext | None = None,
) -> SelectedAd:
    context = context or RequestContext()

    ad_unit = await db.get(AdUnit, ad_unit_id)
    if ad_unit is None:
        raise NoEligibleCampaignError(f"Unknown ad unit: {ad_unit_id}")

    now = datetime.now(timezone.utc)

    stmt = (
        select(Campaign)
        .where(
            Campaign.is_active.is_(True),
            Campaign.start_date <= now,
            Campaign.end_date >= now,
        )
        .join(Creative, Creative.campaign_id == Campaign.id)
        .where(Creative.width == ad_unit.width, Creative.height == ad_unit.height)
    )
    result = await db.execute(stmt)
    candidates = list(result.scalars().unique())

    if not candidates:
        raise NoEligibleCampaignError(
            f"No campaigns match ad unit {ad_unit_id} dimensions"
        )

    targeted = [c for c in candidates if _matches_targeting(c, context)]
    if not targeted:
        raise NoEligibleCampaignError("No campaigns match targeting rules")

    with_budget = [c for c in targeted if await _has_remaining_budget(c)]
    if not with_budget:
        raise NoEligibleCampaignError("No campaigns have remaining budget")

    winner = _rank_and_pick(with_budget)

    creative = next(
        (cr for cr in winner.creatives if cr.width == ad_unit.width and cr.height == ad_unit.height),
        None,
    )
    if creative is None:
        raise NoEligibleCampaignError("Winning campaign has no matching creative")

    return SelectedAd(
        campaign_id=winner.id,
        creative_id=creative.id,
        asset_url=creative.asset_url,
        click_url=creative.click_url,
        width=creative.width,
        height=creative.height,
    )


def _matches_targeting(campaign: Campaign, context: RequestContext) -> bool:
    """Check request context against a campaign's targeting_rules JSON.

    targeting_rules shape (all keys optional -- absence means "no restriction"):
        {
            "countries": ["US", "CA"],
            "device_types": ["mobile"],
            "keywords": ["travel", "outdoors"]
        }
    """
    rules = campaign.targeting_rules or {}

    countries = rules.get("countries")
    if countries and context.country not in countries:
        return False

    device_types = rules.get("device_types")
    if device_types and context.device_type not in device_types:
        return False

    keywords = rules.get("keywords")
    if keywords:
        page_keywords = set(context.page_keywords or [])
        if not page_keywords.intersection(keywords):
            return False

    return True


async def _has_remaining_budget(campaign: Campaign) -> bool:
    """Check Redis fast-path spend counter against the campaign's daily cap.

    Spend is incremented by the event-tracking service on every impression/click.
    Falling back to "allow" if Redis is unreachable is a deliberate choice --
    better to slightly overspend a campaign than to serve zero ads on a Redis
    outage. Adjust for your risk tolerance.
    """
    if campaign.daily_cap is None:
        return True

    key = f"campaign:{campaign.id}:spend:{_today_key()}"
    try:
        spend_raw = await redis_client.get(key)
    except Exception:
        return True

    spend = float(spend_raw) if spend_raw is not None else 0.0
    return spend < campaign.daily_cap


def _rank_and_pick(campaigns: list[Campaign]) -> Campaign:
    """Highest priority wins; ties broken with weighted random choice."""
    max_priority = max(c.priority for c in campaigns)
    top_tier = [c for c in campaigns if c.priority == max_priority]
    return random.choice(top_tier)


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
