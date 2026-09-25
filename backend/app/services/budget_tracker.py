"""Records impression/click events and updates real-time budget + dashboard state.

Writes happen in two places on purpose:
  - Redis: incremented synchronously, read by ad_selector on every ad request
    (must be fast).
  - Postgres: the durable log used for historical analytics and billing.

A short-lived Redis outage means budget enforcement is temporarily loose
(see ad_selector._has_remaining_budget), but events are always durably
recorded in Postgres via this function.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from app.core.redis_client import DASHBOARD_METRICS_CHANNEL, redis_client
from app.db.session import async_session_factory
from app.models.event import Event

# Simplified flat-rate pricing for the reference implementation.
# Swap for real CPM/CPC pricing pulled from the campaign in a production build.
_COST_PER_EVENT = {
    "impression": Decimal("0.001"),  # $1 CPM
    "click": Decimal("0.10"),
}


async def record_event(event_type: str, ad_unit_id: int, creative_id: int) -> None:
    if event_type not in _COST_PER_EVENT:
        raise ValueError(f"Unknown event type: {event_type}")

    async with async_session_factory() as db:
        campaign_id = await _campaign_id_for_creative(db, creative_id)

        event = Event(
            ad_unit_id=ad_unit_id,
            campaign_id=campaign_id,
            creative_id=creative_id,
            type=event_type,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()

    await _increment_spend(campaign_id, _COST_PER_EVENT[event_type])
    await _publish_dashboard_update(event_type, campaign_id, ad_unit_id)


async def _campaign_id_for_creative(db, creative_id: int) -> int:
    from app.models.creative import Creative  # local import avoids circular import

    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise ValueError(f"Unknown creative_id: {creative_id}")
    return creative.campaign_id


async def _increment_spend(campaign_id: int, amount: Decimal) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"campaign:{campaign_id}:spend:{today}"
    await redis_client.incrbyfloat(key, float(amount))
    await redis_client.expire(key, 60 * 60 * 48)  # keep 2 days for safety


async def _publish_dashboard_update(event_type: str, campaign_id: int, ad_unit_id: int) -> None:
    payload = {
        "type": event_type,
        "campaign_id": campaign_id,
        "ad_unit_id": ad_unit_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await redis_client.publish(DASHBOARD_METRICS_CHANNEL, json.dumps(payload))
