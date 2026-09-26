"""Records tracking events, manages event costs, and triggers real-time metrics updates."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional

from app.db.session import async_session_factory
from app.models.creative import Creative
from app.models.event import Event, EventType
from app.services.ad_selector import record_spend

_COST_PER_EVENT: Dict[EventType, Decimal] = {
    EventType.IMPRESSION: Decimal("0.001000"),  # $1.00 CPM
    EventType.CLICK: Decimal("0.100000"),       # $0.10 CPC
    EventType.CONVERSION: Decimal("1.000000"),   # $1.00 CPA
}


async def record_event(
    event_type: EventType | str,
    ad_unit_id: int,
    creative_id: int,
    user_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    event_id: Optional[str] = None,
) -> None:
    """Records an impression or click event and updates campaign spend."""
    if isinstance(event_type, str):
        try:
            enum_event_type = EventType(event_type)
        except ValueError:
            raise ValueError(f"Unknown event type string: {event_type}")
    else:
        enum_event_type = event_type

    if enum_event_type not in _COST_PER_EVENT:
        raise ValueError(f"Unsupported tracking cost type: {enum_event_type}")

    cost = _COST_PER_EVENT[enum_event_type]

    async with async_session_factory() as db:
        campaign_id = await _campaign_id_for_creative(db, creative_id)

        event = Event(
            event_id=event_id,
            ad_unit_id=ad_unit_id,
            campaign_id=campaign_id,
            creative_id=creative_id,
            type=enum_event_type,
            cost=cost,
            is_valid=True,
            user_ip=user_ip,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()

    record_spend(campaign_id, cost)
    await _emit_dashboard_update(enum_event_type.value, campaign_id, ad_unit_id)


async def _campaign_id_for_creative(db, creative_id: int) -> int:
    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise ValueError(f"Unknown creative_id: {creative_id}")
    return creative.campaign_id


async def _emit_dashboard_update(event_type: str, campaign_id: int, ad_unit_id: int) -> None:
    """Emits real-time dashboard updates to connected Socket.IO sockets."""
    from app.sockets.dashboard_ns import emit_metric_update

    payload = {
        "type": event_type,
        "campaign_id": campaign_id,
        "ad_unit_id": ad_unit_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await emit_metric_update(payload)