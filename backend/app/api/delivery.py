"""Publisher-facing REST ad delivery and event tracking endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.ad_unit import AdUnit
from app.models.creative import Creative, ReviewStatus
from app.services.ad_selector import NoEligibleCampaignError, RequestContext, select_ad
from app.services.budget_tracker import record_event
from app.services.publisher_auth import authenticate_publisher

router = APIRouter(prefix="/delivery", tags=["Publisher Ad Delivery"])


class ServedAd(BaseModel):
    campaign_id: int
    creative_id: int
    asset_url: str
    click_url: str
    width: int
    height: int
    format: str


class AdRequestResponse(BaseModel):
    ad: ServedAd | None
    reason: str | None = None


class AdEvent(BaseModel):
    ad_unit_id: int
    creative_id: int
    event_id: str = Field(min_length=1, max_length=128)
    visitor_id: str | None = Field(default=None, max_length=128)


@router.get("/ad/{ad_unit_id}", response_model=AdRequestResponse, summary="Request an ad for an ad unit")
async def request_ad(
    ad_unit_id: int,
    response: Response,
    publisher_key: str = Header(alias="X-Publisher-Key"),
    country: str | None = Query(default=None, max_length=2),
    device_type: str | None = Query(default=None, max_length=32),
    page_keywords: list[str] = Query(default=[]),
    db: AsyncSession = Depends(get_db),
) -> AdRequestResponse:
    response.headers["Cache-Control"] = "no-store"
    publisher = await authenticate_publisher(publisher_key)
    if publisher is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid publisher key")

    belongs_to_publisher = await db.scalar(
        select(AdUnit.id).where(AdUnit.id == ad_unit_id, AdUnit.publisher_id == publisher.id)
    )
    if belongs_to_publisher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad unit not found")

    context = RequestContext(country=country, device_type=device_type, page_keywords=page_keywords)
    try:
        selected = await select_ad(db, ad_unit_id, context)
    except NoEligibleCampaignError as exc:
        return AdRequestResponse(ad=None, reason=str(exc))

    return AdRequestResponse(ad=ServedAd(**selected.__dict__))


@router.post("/events/{event_type}", status_code=status.HTTP_204_NO_CONTENT, summary="Record an ad impression or click")
async def track_ad_event(
    event_type: Literal["impression", "click"],
    payload: AdEvent,
    request: Request,
    publisher_key: str = Header(alias="X-Publisher-Key"),
    db: AsyncSession = Depends(get_db),
) -> None:
    publisher = await authenticate_publisher(publisher_key)
    if publisher is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid publisher key")

    unit = await db.get(AdUnit, payload.ad_unit_id)
    if unit is None or unit.publisher_id != publisher.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad unit not found")
    creative_matches_unit = await db.scalar(
        select(Creative.id).where(
            Creative.id == payload.creative_id,
            Creative.width == unit.width,
            Creative.height == unit.height,
            Creative.is_active.is_(True),
            Creative.review_status == ReviewStatus.APPROVED,
        )
    )
    if creative_matches_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Creative not found")

    client = request.client
    user_agent = request.headers.get("user-agent", "")[:512] or None
    country = (request.headers.get("cf-ipcountry") or request.headers.get("x-country-code") or "")[:2] or None
    await record_event(
        event_type=event_type,
        ad_unit_id=payload.ad_unit_id,
        creative_id=payload.creative_id,
        event_id=payload.event_id,
        visitor_id=payload.visitor_id,
        user_ip=client.host if client else None,
        user_agent=user_agent,
        country_code=country,
    )
