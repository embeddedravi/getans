"""Ad selection service for auction evaluation, dimension matching, and targeting."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import random
from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.advertiser import AccountStatus, Advertiser
from app.models.campaign import BiddingStrategy, Campaign, CampaignStatus
from app.models.creative import Creative, ReviewStatus
from app.models.event import Event, EventType
from app.models.publisher import PublisherStatus

@dataclass
class RequestContext:
    country: Optional[str] = None
    device_type: Optional[str] = None
    page_keywords: List[str] = field(default_factory=list)


@dataclass
class SelectedAd:
    campaign_id: int
    creative_id: int
    asset_url: str
    click_url: str
    width: int
    height: int
    format: str = "image"


class NoEligibleCampaignError(Exception):
    """Raised when no campaign can be served for a given ad unit/context."""


async def select_ad(
    db: AsyncSession,
    ad_unit_id: int,
    context: Optional[RequestContext] = None,
) -> SelectedAd:
    """Evaluates candidate campaigns matching dimensions, targeting, and budget rules."""
    context = context or RequestContext()

    ad_unit = await db.get(AdUnit, ad_unit_id)
    if (
        ad_unit is None
        or not ad_unit.is_active
        or ad_unit.status != AdUnitStatus.APPROVED
        or ad_unit.publisher.status != PublisherStatus.ACTIVE
        or not ad_unit.publisher.is_active
    ):
        raise NoEligibleCampaignError(f"Ad unit unavailable or inactive: {ad_unit_id}")

    now = datetime.now(timezone.utc)

    # Query active, scheduled campaigns with approved creatives matching slot dimensions
    stmt = (
        select(Campaign)
        .options(selectinload(Campaign.creatives))
        .where(
            Campaign.is_active.is_(True),
            Campaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.SCHEDULED]),
            Campaign.start_date <= now,
            or_(Campaign.end_date.is_(None), Campaign.end_date >= now),
        )
        .join(Advertiser, Campaign.advertiser_id == Advertiser.id)
        .where(Advertiser.status == AccountStatus.ACTIVE)
        .join(Creative, Creative.campaign_id == Campaign.id)
        .where(
            Creative.is_active.is_(True),
            Creative.review_status == ReviewStatus.APPROVED,
            Creative.width == ad_unit.width,
            Creative.height == ad_unit.height,
        )
    )

    result = await db.execute(stmt)
    candidates = list(result.scalars().unique())

    if not candidates:
        raise NoEligibleCampaignError(
            f"No active campaigns match ad unit {ad_unit_id} dimensions ({ad_unit.width}x{ad_unit.height})"
        )

    # 1. Filter by targeting rules
    targeted = [c for c in candidates if _matches_targeting(c, context)]
    if not targeted:
        raise NoEligibleCampaignError("No campaigns match request targeting parameters")

    # 2. Filter by reserve floor price and remaining budget
    eligible = [
        c for c in targeted
        if (
            (c.bidding_strategy != BiddingStrategy.CPM or c.bid_amount >= ad_unit.reserve_price)
            and await _has_remaining_budget(db, c)
        )
    ]
    if not eligible:
        raise NoEligibleCampaignError("No campaigns satisfy budget or floor price constraints")

    # 3. Select winning candidate
    winner = _rank_and_pick(eligible)

    # Find the matching creative payload
    creative = next(
        (
            cr
            for cr in winner.creatives
            if cr.is_active
            and cr.review_status == ReviewStatus.APPROVED
            and cr.width == ad_unit.width
            and cr.height == ad_unit.height
        ),
        None,
    )
    if creative is None:
        raise NoEligibleCampaignError("Winning campaign missing compatible creative asset")

    return SelectedAd(
        campaign_id=winner.id,
        creative_id=creative.id,
        asset_url=creative.asset_url,
        click_url=creative.click_url,
        width=creative.width,
        height=creative.height,
        format=creative.format.value,
    )


def _matches_targeting(campaign: Campaign, context: RequestContext) -> bool:
    """Evaluates contextual match rules stored in JSONB targeting payload."""
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


async def _has_remaining_budget(db: AsyncSession, campaign: Campaign) -> bool:
    """Validates campaign spend against total and daily budget limits."""
    if campaign.total_budget is not None and campaign.spent_amount >= campaign.total_budget:
        return False
    if campaign.total_budget is None:
        # Uncapped campaigns spend directly from the available wallet on their
        # billable event. Require enough wallet for at least one event.
        if campaign.bidding_strategy == BiddingStrategy.CPM:
            required = campaign.bid_amount / Decimal("1000")
        else:
            required = campaign.bid_amount
        if campaign.advertiser.balance < required:
            return False

    if campaign.daily_cap is None:
        return True

    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    spend = await db.scalar(
        select(func.coalesce(func.sum(Event.cost), 0)).where(
            Event.campaign_id == campaign.id,
            Event.type.in_([EventType.IMPRESSION, EventType.CLICK, EventType.CONVERSION]),
            Event.is_valid.is_(True),
            Event.timestamp >= start,
        )
    )
    spend = Decimal(str(spend or 0))
    return spend < campaign.daily_cap


def _rank_and_pick(campaigns: List[Campaign]) -> Campaign:
    """Ranks candidate campaigns by priority tier and selects winner."""
    max_priority = max(c.priority for c in campaigns)
    top_tier = [c for c in campaigns if c.priority == max_priority]
    return random.choice(top_tier)
