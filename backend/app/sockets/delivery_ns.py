"""
Socket.IO namespace handling publisher-facing ad delivery.

Events:
    client -> server: "request_ad"   { ad_unit_id, api_key, context? }
    server -> client: "serve_ad"     { creative_id, asset_url, click_url, width, height }
    server -> client: "no_fill"      { reason }
    client -> server: "impression"   { creative_id, ad_unit_id }
    client -> server: "click"        { creative_id, ad_unit_id }
"""

from __future__ import annotations

import logging

import socketio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.ad_selector import (
    NoEligibleCampaignError,
    RequestContext,
    select_ad,
)
from app.services.budget_tracker import record_event
from app.services.publisher_auth import authenticate_publisher

logger = logging.getLogger(__name__)


class DeliveryNamespace(socketio.AsyncNamespace):
    async def on_connect(self, sid: str, environ: dict) -> None:
        logger.debug("Delivery client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.debug("Delivery client disconnected: %s", sid)

    async def on_request_ad(self, sid: str, data: dict) -> None:
        ad_unit_id = data.get("ad_unit_id")
        api_key = data.get("api_key")

        if not ad_unit_id or not api_key:
            await self.emit("no_fill", {"reason": "missing_params"}, to=sid)
            return

        publisher = await authenticate_publisher(api_key)
        if publisher is None:
            await self.emit("no_fill", {"reason": "unauthorized"}, to=sid)
            return

        context = RequestContext(
            country=data.get("context", {}).get("country"),
            device_type=data.get("context", {}).get("device_type"),
            page_keywords=data.get("context", {}).get("page_keywords"),
        )

        async for db in get_session():
            await self._serve(db, sid, ad_unit_id, context)

    async def _serve(
        self,
        db: AsyncSession,
        sid: str,
        ad_unit_id: int,
        context: RequestContext,
    ) -> None:
        try:
            ad = await select_ad(db, ad_unit_id, context)
        except NoEligibleCampaignError as exc:
            logger.info("No fill for ad_unit=%s: %s", ad_unit_id, exc)
            await self.emit("no_fill", {"reason": str(exc)}, to=sid)
            return

        await self.emit(
            "serve_ad",
            {
                "campaign_id": ad.campaign_id,
                "creative_id": ad.creative_id,
                "asset_url": ad.asset_url,
                "click_url": ad.click_url,
                "width": ad.width,
                "height": ad.height,
            },
            to=sid,
        )

    async def on_impression(self, sid: str, data: dict) -> None:
        await record_event(
            event_type="impression",
            ad_unit_id=data.get("ad_unit_id"),
            creative_id=data.get("creative_id"),
        )

    async def on_click(self, sid: str, data: dict) -> None:
        await record_event(
            event_type="click",
            ad_unit_id=data.get("ad_unit_id"),
            creative_id=data.get("creative_id"),
        )


def register_delivery_namespace(sio: socketio.AsyncServer) -> None:
    sio.register_namespace(DeliveryNamespace("/delivery"))
