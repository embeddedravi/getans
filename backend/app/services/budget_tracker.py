"""Records impression/click events and updates in-memory budget state."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.db.session import async_session_factory
from app.models.event import Event
from app.services.ad_selector import record_spend

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

    record_spend(campaign_id, float(_COST_PER_EVENT[event_type]))
    await _emit_dashboard_update(event_type, campaign_id, ad_unit_id)


async def _campaign_id_for_creative(db, creative_id: int) -> int:
    from app.models.creative import Creative

    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise ValueError(f"Unknown creative_id: {creative_id}")
    return creative.campaign_id


async def _emit_dashboard_update(event_type: str, campaign_id: int, ad_unit_id: int) -> None:
    """Emit straight to connected dashboard sockets -- no Redis pub/sub needed
    since this runs in the same process as the Socket.IO server."""
    from app.sockets.dashboard_ns import emit_metric_update

    payload = {
        "type": event_type,
        "campaign_id": campaign_id,
        "ad_unit_id": ad_unit_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await emit_metric_update(payload)