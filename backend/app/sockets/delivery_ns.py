"""
Socket.IO namespace handling publisher-facing ad delivery.

Events:
    client -> server: "request_ad"   { ad_unit_id, api_key, context? }
    server -> client: "serve_ad"     { creative_id, asset_url, click_url, width, height }
    server -> client: "no_fill"      { reason }
    client -> server: "impression"   { creative_id, ad_unit_id }
    client -> server: "click"        { creative_id, ad_unit_id }
    client -> server: "report_ad"    { api_key, ad_unit_id, creative_id, visitor_id, reason }
"""

from __future__ import annotations

import logging
import hashlib

import socketio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.ad_report import AdReport
from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.creative import Creative
from app.services.ad_selector import (
    NoEligibleCampaignError,
    RequestContext,
    select_ad,
)
from app.services.budget_tracker import record_event
from app.services.publisher_auth import authenticate_publisher

logger = logging.getLogger(__name__)
AD_REPORT_THRESHOLD = 3
AD_REPORT_REASONS = {"misleading", "adult_content", "inappropriate", "scam", "other"}


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
        session = await self.get_session(sid)
        session["country_code"] = _normalize_country(context.country)
        await self.save_session(sid, session)

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
        metadata = await self._event_metadata(sid, data)
        await record_event(
            event_type="impression",
            ad_unit_id=data.get("ad_unit_id"),
            creative_id=data.get("creative_id"),
            event_id=data.get("event_id"),
            visitor_id=data.get("visitor_id"),
            **metadata,
        )

    async def on_click(self, sid: str, data: dict) -> None:
        metadata = await self._event_metadata(sid, data)
        await record_event(
            event_type="click",
            ad_unit_id=data.get("ad_unit_id"),
            creative_id=data.get("creative_id"),
            event_id=data.get("event_id"),
            visitor_id=data.get("visitor_id"),
            **metadata,
        )

    async def _event_metadata(self, sid: str, data: dict) -> dict[str, str | None]:
        """Extract client metadata from the socket request and ad request context."""
        environ = self.server.get_environ(sid, namespace=self.namespace) or {}
        session = await self.get_session(sid)
        country = _normalize_country(
            data.get("country_code")
            or session.get("country_code")
            or environ.get("HTTP_CF_IPCOUNTRY")
            or environ.get("HTTP_CLOUDFRONT_VIEWER_COUNTRY")
            or environ.get("HTTP_X_COUNTRY_CODE")
            or environ.get("GEOIP_COUNTRY_CODE")
        )

        user_ip = environ.get("REMOTE_ADDR")
        if isinstance(user_ip, str):
            user_ip = user_ip.strip()[:45] or None
        else:
            user_ip = None

        user_agent = environ.get("HTTP_USER_AGENT")
        if isinstance(user_agent, str):
            user_agent = user_agent[:512] or None
        else:
            user_agent = None

        return {"user_ip": user_ip, "user_agent": user_agent, "country_code": country}

    async def on_report_ad(self, sid: str, data: dict) -> dict:
        """Record one report per distinct visitor in the current review round."""
        api_key = data.get("api_key")
        visitor_id = data.get("visitor_id")
        reason = data.get("reason")
        try:
            ad_unit_id = int(data.get("ad_unit_id"))
            creative_id = int(data.get("creative_id"))
        except (TypeError, ValueError):
            return {"ok": False, "message": "Invalid ad or slot."}

        if (
            not isinstance(api_key, str)
            or not isinstance(visitor_id, str)
            or len(visitor_id) < 16
            or len(visitor_id) > 128
            or not isinstance(reason, str)
            or reason not in AD_REPORT_REASONS
        ):
            return {"ok": False, "message": "Invalid report details."}

        publisher = await authenticate_publisher(api_key)
        if publisher is None:
            return {"ok": False, "message": "Publisher authentication failed."}

        visitor_hash = hashlib.sha256(visitor_id.encode("utf-8")).hexdigest()
        async for db in get_session():
            unit_result = await db.execute(
                select(AdUnit)
                .where(AdUnit.id == ad_unit_id, AdUnit.publisher_id == publisher.id)
                .with_for_update()
            )
            ad_unit = unit_result.scalar_one_or_none()
            if ad_unit is None:
                return {"ok": False, "message": "Ad slot not found."}

            creative = await db.get(Creative, creative_id)
            if (
                creative is None
                or creative.width != ad_unit.width
                or creative.height != ad_unit.height
            ):
                return {"ok": False, "message": "The reported creative does not match this slot."}

            existing = await db.scalar(
                select(AdReport.id).where(
                    AdReport.ad_unit_id == ad_unit.id,
                    AdReport.review_round == ad_unit.report_review_round,
                    AdReport.reporter_hash == visitor_hash,
                )
            )
            if existing is not None:
                return {"ok": True, "duplicate": True, "message": "You have already reported an ad in this slot."}

            db.add(
                AdReport(
                    ad_unit_id=ad_unit.id,
                    creative_id=creative.id,
                    reporter_hash=visitor_hash,
                    review_round=ad_unit.report_review_round,
                    reason=reason,
                )
            )
            await db.flush()

            report_count = await db.scalar(
                select(func.count(AdReport.id)).where(
                    AdReport.ad_unit_id == ad_unit.id,
                    AdReport.review_round == ad_unit.report_review_round,
                )
            )
            if report_count >= AD_REPORT_THRESHOLD and ad_unit.status == AdUnitStatus.APPROVED:
                ad_unit.status = AdUnitStatus.PENDING_REVIEW
                ad_unit.is_active = False
                logger.warning(
                    "Ad unit %s moved to pending review after %s visitor reports",
                    ad_unit.id,
                    report_count,
                )

            await db.commit()
            return {
                "ok": True,
                "duplicate": False,
                "report_count": report_count,
                "review_threshold": AD_REPORT_THRESHOLD,
                "pending_review": ad_unit.status == AdUnitStatus.PENDING_REVIEW,
                "message": (
                    "Thanks. This ad slot has been paused for review."
                    if ad_unit.status == AdUnitStatus.PENDING_REVIEW
                    else "Thanks. Your report has been recorded."
                ),
            }

        return {"ok": False, "message": "Could not record the report."}


def _normalize_country(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    country = value.strip().upper()
    return country if len(country) == 2 and country.isalpha() else None


def register_delivery_namespace(sio: socketio.AsyncServer) -> None:
    sio.register_namespace(DeliveryNamespace("/delivery"))
