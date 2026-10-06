"""Admin approval endpoints for publishers, advertisers, and ad units."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.advertiser import Advertiser, AccountStatus
from app.models.publisher import Publisher, PublisherStatus
from app.models.user import User
from app.schemas.add_unit import AdUnitOut, AdUnitReview
from app.schemas.advertiser import AdvertiserOut, AdvertiserReview
from app.schemas.publisher import PublisherOut, PublisherReview

router = APIRouter(prefix="/admin", tags=["Admin Approvals"])


@router.get(
    "/approvals/pending",
    response_model=Dict[str, Any],
    summary="List all entities awaiting admin approval",
)
async def list_pending_approvals(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "staff")),
) -> Dict[str, Any]:
    """Returns pending publishers, advertisers, and ad units in a single payload."""
    publishers = list(
        (await db.execute(
            select(Publisher).where(Publisher.status == PublisherStatus.PENDING_APPROVAL)
        )).scalars().all()
    )
    advertisers = list(
        (await db.execute(
            select(Advertiser).where(Advertiser.status == AccountStatus.PENDING_VERIFICATION)
        )).scalars().all()
    )
    ad_units = list(
        (await db.execute(
            select(AdUnit).where(AdUnit.status == AdUnitStatus.PENDING_REVIEW)
        )).scalars().all()
    )
    return {
        "publishers": [PublisherOut.model_validate(p).model_dump(mode="json") for p in publishers],
        "advertisers": [AdvertiserOut.model_validate(a).model_dump(mode="json") for a in advertisers],
        "ad_units": [AdUnitOut.model_validate(u).model_dump(mode="json") for u in ad_units],
    }


@router.patch(
    "/publishers/{publisher_id}/review",
    response_model=PublisherOut,
    summary="Approve or reject a publisher",
)
async def review_publisher(
    publisher_id: int,
    payload: PublisherReview,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "staff")),
) -> Publisher:
    """Sets a publisher's status to active (approved) or rejected."""
    publisher = await db.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publisher not found")
    if payload.status not in (PublisherStatus.ACTIVE, PublisherStatus.REJECTED):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review status must be active or rejected")
    publisher.status = payload.status
    publisher.is_active = payload.status == PublisherStatus.ACTIVE
    publisher.rejection_reason = (
        payload.rejection_reason.strip() if payload.status == PublisherStatus.REJECTED else None
    )
    await db.commit()
    await db.refresh(publisher)
    return publisher


@router.patch(
    "/advertisers/{advertiser_id}/review",
    response_model=AdvertiserOut,
    summary="Approve or reject an advertiser",
)
async def review_advertiser(
    advertiser_id: int,
    payload: AdvertiserReview,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "staff")),
) -> Advertiser:
    """Sets an advertiser's status to active (approved) or rejected."""
    advertiser = await db.get(Advertiser, advertiser_id)
    if advertiser is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advertiser not found")
    if payload.status not in (AccountStatus.ACTIVE, AccountStatus.REJECTED):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review status must be active or rejected")
    advertiser.status = payload.status
    advertiser.is_verified = payload.status == AccountStatus.ACTIVE
    advertiser.rejection_reason = (
        payload.rejection_reason.strip() if payload.status == AccountStatus.REJECTED else None
    )
    await db.commit()
    await db.refresh(advertiser)
    return advertiser


@router.patch(
    "/ad-units/{ad_unit_id}/review",
    response_model=AdUnitOut,
    summary="Approve or reject an ad unit",
)
async def review_ad_unit(
    ad_unit_id: int,
    payload: AdUnitReview,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "staff")),
) -> AdUnit:
    """Sets an ad unit's review status to approved or rejected."""
    ad_unit = await db.get(AdUnit, ad_unit_id)
    if ad_unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad unit not found")
    if payload.status not in (AdUnitStatus.APPROVED, AdUnitStatus.REJECTED):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review status must be approved or rejected")
    ad_unit.status = payload.status
    ad_unit.is_active = payload.status == AdUnitStatus.APPROVED
    ad_unit.rejection_reason = (
        payload.rejection_reason.strip() if payload.status == AdUnitStatus.REJECTED else None
    )
    await db.commit()
    await db.refresh(ad_unit)
    return ad_unit
