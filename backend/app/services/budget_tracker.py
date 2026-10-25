"""Records tracking events, manages event costs, and triggers real-time metrics updates."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select

from app.db.session import async_session_factory
from app.models.ad_unit import AdUnit
from app.models.campaign import BiddingStrategy, Campaign
from app.models.creative import Creative
from app.models.event import Event, EventType
from app.models.advertiser import Advertiser
from app.models.publisher import Publisher

_BILLABLE_TYPES = {EventType.IMPRESSION, EventType.CLICK, EventType.CONVERSION}


class BudgetExceededError(Exception):
    """Raised when an event would exceed a campaign cap or available funds."""


async def record_event(
    event_type: EventType | str,
    ad_unit_id: int,
    creative_id: int,
    user_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    event_id: Optional[str] = None,
    country_code: Optional[str] = None,
    visitor_id: Optional[str] = None,
) -> None:
    """Records a billable event once per visitor, ad unit, event type, and UTC day."""
    if isinstance(event_type, str):
        try:
            enum_event_type = EventType(event_type)
        except ValueError:
            raise ValueError(f"Unknown event type string: {event_type}")
    else:
        enum_event_type = event_type

    if enum_event_type not in _BILLABLE_TYPES | {EventType.VIEWABLE_IMPRESSION}:
        raise ValueError(f"Unsupported tracking cost type: {enum_event_type}")

    timestamp = datetime.now(timezone.utc)
    dedupe_key = None
    if isinstance(visitor_id, str) and 1 <= len(visitor_id) <= 128:
        visitor_hash = hashlib.sha256(visitor_id.encode("utf-8")).hexdigest()
        identity = f"{visitor_hash}:{ad_unit_id}:{enum_event_type.value}:{timestamp:%Y-%m-%d}"
        dedupe_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()

    live = None
    async with async_session_factory() as db:
        campaign = await _campaign_for_creative(db, creative_id, lock=True)
        campaign_id, advertiser_id = campaign.id, campaign.advertiser_id
        advertiser = None
        if campaign.total_budget is None:
            advertiser = await db.scalar(
                select(Advertiser).where(Advertiser.id == advertiser_id).with_for_update()
            )
        publisher = await db.scalar(
            select(Publisher).join(AdUnit, AdUnit.publisher_id == Publisher.id)
            .where(AdUnit.id == ad_unit_id).with_for_update()
        )
        if publisher is None:
            raise ValueError(f"Unknown ad_unit_id: {ad_unit_id}")
        publisher_id = publisher.id

        cost = _event_cost(campaign, enum_event_type)
        if cost:
            if campaign.total_budget is not None and campaign.spent_amount + cost > campaign.total_budget:
                raise BudgetExceededError("Campaign total budget is exhausted")
            if advertiser is not None:
                if advertiser.balance < cost:
                    raise BudgetExceededError("Advertiser wallet has insufficient funds")
                advertiser.balance -= cost
            if campaign.daily_cap is not None:
                day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                daily_spend = await db.scalar(
                    select(func.coalesce(func.sum(Event.cost), 0)).where(
                        Event.campaign_id == campaign_id,
                        Event.type.in_(_BILLABLE_TYPES),
                        Event.is_valid.is_(True),
                        Event.timestamp >= day_start,
                    )
                )
                if Decimal(str(daily_spend or 0)) + cost > campaign.daily_cap:
                    raise BudgetExceededError("Campaign daily cap is exhausted")

        event = Event(
            event_id=event_id,
            dedupe_key=dedupe_key,
            ad_unit_id=ad_unit_id,
            campaign_id=campaign_id,
            creative_id=creative_id,
            type=enum_event_type,
            cost=cost,
            is_valid=True,
            user_ip=user_ip,
            user_agent=user_agent,
            country_code=country_code,
            timestamp=timestamp,
        )
        db.add(event)
        try:
            campaign.spent_amount += cost
            publisher.unpaid_earnings += (cost * publisher.revenue_share_percentage / Decimal("100"))
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return

        live = {
            "id": event.id,
            "type": enum_event_type.value,
            "campaign_id": campaign_id,
            "campaign_name": await db.scalar(select(Campaign.name).where(Campaign.id == campaign_id)),
            "ad_unit_id": ad_unit_id,
            "slot_name": await db.scalar(select(AdUnit.slot_name).where(AdUnit.id == ad_unit_id)),
            "creative_id": creative_id,
            "country_code": country_code,
            "cost": float(cost),
            "timestamp": timestamp.isoformat(),
        }

    await _emit_dashboard_update(enum_event_type.value, campaign_id, ad_unit_id, advertiser_id, publisher_id)
    await _emit_live_event(live, advertiser_id=advertiser_id, publisher_id=publisher_id)


async def _emit_live_event(
    payload: dict,
    *,
    advertiser_id: int | None,
    publisher_id: int | None,
) -> None:
    from app.sockets.dashboard_ns import emit_live_event
    await emit_live_event(payload, advertiser_id=advertiser_id, publisher_id=publisher_id)


def _event_cost(campaign: Campaign, event_type: EventType) -> Decimal:
    """Compute the contracted cost from the campaign's bidding strategy."""
    if event_type == EventType.VIEWABLE_IMPRESSION:
        return Decimal("0.000000")
    if campaign.bidding_strategy == BiddingStrategy.CPM and event_type == EventType.IMPRESSION:
        amount = campaign.bid_amount / Decimal("1000")
    elif campaign.bidding_strategy == BiddingStrategy.CPC and event_type == EventType.CLICK:
        amount = campaign.bid_amount
    elif campaign.bidding_strategy == BiddingStrategy.CPA and event_type == EventType.CONVERSION:
        amount = campaign.bid_amount
    else:
        return Decimal("0.000000")
    return amount.quantize(Decimal("0.000001"))


async def _campaign_for_creative(db, creative_id: int, lock: bool = False) -> Campaign:
    stmt = select(Campaign).join(Creative, Creative.campaign_id == Campaign.id).where(Creative.id == creative_id)
    if lock:
        stmt = stmt.with_for_update()
    campaign = await db.scalar(stmt)
    if campaign is None:
        raise ValueError(f"Unknown creative_id: {creative_id}")
    return campaign


async def _emit_dashboard_update(
    event_type: str,
    campaign_id: int,
    ad_unit_id: int,
    advertiser_id: int,
    publisher_id: Optional[int],
) -> None:
    """Pushes a metric to the dashboard rooms that are allowed to see it."""
    from app.sockets.dashboard_ns import emit_metric_update

    payload = {
        "type": event_type,
        "campaign_id": campaign_id,
        "ad_unit_id": ad_unit_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await emit_metric_update(payload, advertiser_id=advertiser_id, publisher_id=publisher_id)
