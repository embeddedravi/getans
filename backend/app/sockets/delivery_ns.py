"""
Socket.IO namespace handling publisher-facing ad delivery.

Events:
    client -> server: "request_ad"           { ad_unit_id, api_key, context? }
    server -> client: "serve_ad"             { creative_id, asset_url, click_url, width, height }
    server -> client: "no_fill"              { reason }
    client -> server: "impression"           { ad_unit_id, creative_id, visitor_id, serve_token, event_id }
    client -> server: "click"                { ad_unit_id, creative_id, visitor_id, serve_token, event_id }
    client -> server: "viewable_impression"  { ad_unit_id, creative_id, visitor_id, serve_token, event_id }
    client -> server: "report_ad"            { api_key, ad_unit_id, creative_id, visitor_id, reason }
"""

from __future__ import annotations

import logging
import hashlib
import secrets
from decimal import Decimal

import socketio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory, get_session
from app.models.ad_report import AdReport
from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.creative import Creative
from app.services.ad_selector import (
    NoEligibleCampaignError,
    RequestContext,
    select_ad,
)
from app.services.budget_tracker import BudgetExceededError, record_event
from app.services.publisher_auth import authenticate_publisher
from app.services.serve_token import issue_serve_token, verify_serve_token

logger = logging.getLogger(__name__)
AD_REPORT_THRESHOLD = 3
AD_REPORT_REASONS = {"misleading", "adult_content", "inappropriate", "scam", "other"}


class DeliveryNamespace(socketio.AsyncNamespace):
    async def on_connect(self, sid: str, environ: dict) -> None:
        logger.debug("Delivery client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.debug("Delivery client disconnected: %s", sid)

    async def on_request_ad(self, sid: str, data: dict) -> None:
        if not isinstance(data, dict):
            await self.emit("no_fill", {"reason": "invalid_params"}, to=sid)
            return
        ad_unit_id = data.get("ad_unit_id")
        api_key = data.get("api_key")

        if not ad_unit_id or not api_key:
            await self.emit("no_fill", {"reason": "missing_params"}, to=sid)
            return

        publisher = await authenticate_publisher(api_key)
        if publisher is None:
            await self.emit("no_fill", {"reason": "unauthorized"}, to=sid)
            return

        environ = (self.server.get_environ(sid, namespace=self.namespace) or {}) if self.server else {}
        origin = environ.get("HTTP_ORIGIN")
        site_url = getattr(publisher, "site_url", None)
        if origin and site_url:
            from urllib.parse import urlsplit
            if (urlsplit(origin).hostname or "").lower() != (urlsplit(site_url).hostname or site_url).lower():
                await self.emit("no_fill", {"reason": "origin_mismatch"}, to=sid)
                return

        client_context = data.get("context")
        if not isinstance(client_context, dict):
            client_context = {}
        country = environ.get("HTTP_CF_IPCOUNTRY") or environ.get("HTTP_CLOUDFRONT_VIEWER_COUNTRY") or environ.get("HTTP_X_COUNTRY_CODE")
        context = RequestContext(country=country, device_type=client_context.get("device_type"), page_keywords=client_context.get("page_keywords"))
        session = await self.get_session(sid)
        session["country_code"] = _normalize_country(country)
        await self.save_session(sid, session)

        async for db in get_session():
            owned = await db.scalar(select(AdUnit.id).where(AdUnit.id == ad_unit_id, AdUnit.publisher_id == publisher.id))
            if owned is None:
                await self.emit("no_fill", {"reason": "ad_unit_not_found"}, to=sid)
                return
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

        token, visitor = issue_serve_token(ad_unit_id, ad.creative_id)
        serve_payload = {
            "campaign_id": ad.campaign_id,
            "creative_id": ad.creative_id,
            "asset_url": ad.asset_url,
            "click_url": ad.click_url,
            "width": ad.width,
            "height": ad.height,
            "format": ad.format,
            "custom_attributes": ad.custom_attributes,
            "html_snippet": ad.html_snippet,
            "serve_token": token,
            "visitor_id": visitor,
        }
        if ad.format == "poll":
            serve_payload["poll_results"] = await self._get_poll_stats(db, ad.creative_id, ad.custom_attributes)

        await self.emit("serve_ad", serve_payload, to=sid)

    async def on_impression(self, sid: str, data: dict) -> None:
        visitor = verify_serve_token(str(data.get("serve_token", "")), data.get("ad_unit_id", 0), data.get("creative_id", 0)) if isinstance(data, dict) else None
        if visitor is None:
            await self.emit("event_rejected", {"reason": "invalid_or_expired_serve_token"}, to=sid)
            return
        metadata = await self._event_metadata(sid, data)
        try:
            await record_event(
                event_type="impression",
                ad_unit_id=data.get("ad_unit_id", 0),
                creative_id=data.get("creative_id", 0),
                event_id=data.get("event_id", ""),
                visitor_id=visitor,
                **metadata,
            )
        except BudgetExceededError as exc:
            await self.emit("event_rejected", {"reason": str(exc)}, to=sid)
        except ValueError as exc:
            await self.emit("event_rejected", {"reason": str(exc)}, to=sid)

    async def on_click(self, sid: str, data: dict) -> None:
        visitor = verify_serve_token(str(data.get("serve_token", "")), data.get("ad_unit_id", 0), data.get("creative_id", 0)) if isinstance(data, dict) else None
        if visitor is None:
            await self.emit("event_rejected", {"reason": "invalid_or_expired_serve_token"}, to=sid)
            return
        metadata = await self._event_metadata(sid, data)
        try:
            await record_event(
                event_type="click",
                ad_unit_id=data.get("ad_unit_id", 0),
                creative_id=data.get("creative_id", 0),
                event_id=data.get("event_id", ""),
                visitor_id=visitor,
                **metadata,
            )
        except BudgetExceededError as exc:
            await self.emit("event_rejected", {"reason": str(exc)}, to=sid)
        except ValueError as exc:
            await self.emit("event_rejected", {"reason": str(exc)}, to=sid)

    async def on_viewable_impression(self, sid: str, data: dict) -> None:
        """Handle viewable impression event (ad entered viewport)."""
        visitor = verify_serve_token(str(data.get("serve_token", "")), data.get("ad_unit_id", 0), data.get("creative_id", 0)) if isinstance(data, dict) else None
        if visitor is None:
            await self.emit("event_rejected", {"reason": "invalid_or_expired_serve_token"}, to=sid)
            return
        metadata = await self._event_metadata(sid, data)
        try:
            await record_event(
                event_type="viewable_impression",
                ad_unit_id=data.get("ad_unit_id", 0),
                creative_id=data.get("creative_id", 0),
                event_id=data.get("event_id", ""),
                visitor_id=visitor,
                **metadata,
            )
        except BudgetExceededError as exc:
            await self.emit("event_rejected", {"reason": str(exc)}, to=sid)
        except ValueError as exc:
            await self.emit("event_rejected", {"reason": str(exc)}, to=sid)

    async def _get_poll_stats(
        self,
        db: AsyncSession,
        creative_id: int,
        custom_attributes: dict | None = None,
    ) -> dict:
        attrs = custom_attributes or {}
        question = attrs.get("poll_question", "")
        options = attrs.get("poll_options", [])
        from app.models.event import Event, EventType
        result = await db.execute(
            select(Event.meta).where(
                Event.creative_id == creative_id,
                Event.type == EventType.POLL_VOTE,
                Event.is_valid.is_(True),
            )
        )
        counts = [0, 0, 0, 0]
        for row in result.scalars():
            if isinstance(row, dict) and "option_index" in row:
                try:
                    idx = int(row["option_index"])
                    if 0 <= idx < 4:
                        counts[idx] += 1
                except (ValueError, TypeError):
                    pass
        total = sum(counts)
        percentages = [round((c / total * 100), 1) if total > 0 else 0.0 for c in counts]
        return {
            "question": question,
            "options": options,
            "counts": counts,
            "percentages": percentages,
            "total_votes": total,
        }

    async def on_poll_vote(self, sid: str, data: dict) -> dict:
        """Handle poll vote interaction event from publisher embed."""
        if not isinstance(data, dict):
            return {"ok": False, "message": "Invalid vote payload"}

        try:
            ad_unit_id = int(data.get("ad_unit_id", 0))
            creative_id = int(data.get("creative_id", 0))
            option_index = int(data.get("option_index", -1))
        except (TypeError, ValueError):
            return {"ok": False, "message": "Invalid ad or option index"}

        if not (0 <= option_index <= 3):
            return {"ok": False, "message": "Option index must be between 0 and 3"}

        serve_token = str(data.get("serve_token", ""))
        visitor = verify_serve_token(serve_token, ad_unit_id, creative_id)
        if visitor is None:
            await self.emit("event_rejected", {"reason": "invalid_or_expired_serve_token"}, to=sid)
            return {"ok": False, "message": "Invalid or expired serve token"}

        metadata = await self._event_metadata(sid, data)
        from app.models.event import Event, EventType
        from app.models.creative import Creative
        from app.models.campaign import Campaign
        from datetime import datetime, timezone
        from sqlalchemy.exc import IntegrityError
        from app.services.budget_tracker import _emit_live_event

        timestamp = datetime.now(timezone.utc)
        visitor_hash = hashlib.sha256(visitor.encode("utf-8")).hexdigest()
        identity = f"{visitor_hash}:{ad_unit_id}:{creative_id}:poll_vote:{timestamp:%Y-%m-%d}"
        dedupe_key = hashlib.sha256(identity.encode("utf-8")).hexdigest()

        event_id = data.get("event_id") or f"pv-{secrets.token_hex(12)}"

        async with async_session_factory() as db:
            creative = await db.get(Creative, creative_id)
            if not creative:
                return {"ok": False, "message": "Creative not found"}

            attrs = creative.custom_attributes or {}
            options = attrs.get("poll_options", [])
            option_text = options[option_index] if 0 <= option_index < len(options) else f"Option {option_index + 1}"

            event = Event(
                event_id=event_id,
                dedupe_key=dedupe_key,
                ad_unit_id=ad_unit_id,
                campaign_id=creative.campaign_id,
                creative_id=creative_id,
                type=EventType.POLL_VOTE,
                cost=Decimal("0.000000"),
                is_valid=True,
                user_ip=metadata.get("user_ip"),
                user_agent=metadata.get("user_agent"),
                country_code=metadata.get("country_code"),
                timestamp=timestamp,
                meta={
                    "option_index": option_index,
                    "option_text": option_text,
                },
            )
            db.add(event)
            already_voted = False
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                already_voted = True

            stats = await self._get_poll_stats(db, creative_id, attrs)

            if not already_voted:
                live = {
                    "id": event.id,
                    "type": EventType.POLL_VOTE.value,
                    "campaign_id": creative.campaign_id,
                    "campaign_name": await db.scalar(select(Campaign.name).where(Campaign.id == creative.campaign_id)),
                    "ad_unit_id": ad_unit_id,
                    "slot_name": await db.scalar(select(AdUnit.slot_name).where(AdUnit.id == ad_unit_id)),
                    "creative_id": creative_id,
                    "country_code": metadata.get("country_code"),
                    "cost": 0.0,
                    "meta": {"option_index": option_index, "option_text": option_text},
                    "timestamp": timestamp.isoformat(),
                }
                campaign = await db.get(Campaign, creative.campaign_id)
                adv_id = campaign.advertiser_id if campaign else None
                pub = await db.scalar(select(AdUnit.publisher_id).where(AdUnit.id == ad_unit_id))
                try:
                    await _emit_live_event(live, advertiser_id=adv_id, publisher_id=pub)
                except Exception:
                    pass

            return {
                "ok": True,
                "already_voted": already_voted,
                "selected_option": option_index,
                "poll_results": stats,
            }

    async def _event_metadata(self, sid: str, data: dict) -> dict[str, str | None]:
        """Extract client metadata from the socket request and ad request context."""
        environ = (self.server.get_environ(sid, namespace=self.namespace) or {}) if self.server else {}
        session = (await self.get_session(sid)) if self.server else {}
        country = _normalize_country(
            environ.get("HTTP_CF_IPCOUNTRY")
            or environ.get("HTTP_CLOUDFRONT_VIEWER_COUNTRY")
            or environ.get("HTTP_X_COUNTRY_CODE")
            or environ.get("GEOIP_COUNTRY_CODE")
            or session.get("country_code")
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
        if not isinstance(data, dict):
            return {"ok": False, "message": "Invalid report details."}
        api_key = data.get("api_key")
        visitor_id = data.get("visitor_id")
        reason = data.get("reason")
        try:
            ad_unit_id = int(data.get("ad_unit_id", 0))
            creative_id = int(data.get("creative_id", 0))
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

        environ = (self.server.get_environ(sid, namespace=self.namespace) or {}) if self.server else {}
        origin = environ.get("HTTP_ORIGIN")
        if origin:
            from urllib.parse import urlsplit
            supplied_host = (urlsplit(origin).hostname or "").lower()
            allowed_hosts = {(urlsplit(publisher.site_url).hostname or publisher.site_url).lower()}
            if getattr(publisher, "domain", None):
                allowed_hosts.add(publisher.domain.lower())
            if supplied_host not in allowed_hosts:
                return {"ok": False, "message": "Origin does not match publisher site."}

        visitor_from_token = verify_serve_token(str(data.get("serve_token", "")), ad_unit_id, creative_id)
        if visitor_from_token is None:
            return {"ok": False, "message": "A valid served ad token is required."}
        visitor_id = visitor_from_token

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
                or not creative.is_active
                or creative.review_status.value != "approved"
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
