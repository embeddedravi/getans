"""
Ad selection service.
...
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_unit import AdUnit
from app.models.campaign import Campaign
from app.models.creative import Creative

# In-memory spend cache: {"campaign_id:YYYY-MM-DD": spend_so_far}
# NOTE: resets on process restart and is per-process only. Fine for a single
# backend instance; will under-enforce daily caps if you ever run multiple
# workers/replicas. See README for the Redis-backed alternative.
_spend_cache: dict[str, float] = {}


@dataclass
class RequestContext:
    country: str | None = None
    device_type: str | None = None
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

    with_budget = [c for c in targeted if _has_remaining_budget(c)]
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


def _has_remaining_budget(campaign: Campaign) -> bool:
    """In-memory replacement for the old Redis-backed spend check.

    No longer async since there's no I/O involved.
    """
    if campaign.daily_cap is None:
        return True

    key = f"{campaign.id}:{_today_key()}"
    spend = _spend_cache.get(key, 0.0)
    return spend < campaign.daily_cap


def record_spend(campaign_id: int, amount: float) -> None:
    """Called by budget_tracker after each impression/click."""
    key = f"{campaign_id}:{_today_key()}"
    _spend_cache[key] = _spend_cache.get(key, 0.0) + amount


def _rank_and_pick(campaigns: list[Campaign]) -> Campaign:
    max_priority = max(c.priority for c in campaigns)
    top_tier = [c for c in campaigns if c.priority == max_priority]
    return random.choice(top_tier)


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")