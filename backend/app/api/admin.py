"""Admin approval endpoints for publishers, advertisers, and ad units."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.ad_report import AdReport
from app.models.advertiser import Advertiser, AccountStatus
from app.models.publisher import Publisher, PublisherStatus
from app.models.user import User, UserRole as UserRoleModel
from app.models.campaign import Campaign
from app.models.event import Event
from app.schemas.add_unit import AdUnitOut, AdUnitReview
from app.schemas.advertiser import AdvertiserOut, AdvertiserReview
from app.schemas.publisher import PublisherOut, PublisherReview
from app.schemas.user import AdminUserOut, AdminUserUpdate

router = APIRouter(prefix="/admin", tags=["Admin Approvals"])


@router.get("/users", response_model=list[AdminUserOut], summary="List dashboard users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return list(result.scalars().all())


@router.patch("/users/{user_id}", response_model=AdminUserOut, summary="Update a dashboard user")
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Superuser accounts cannot be changed here")
    if user.id == admin.id and (payload.role != UserRoleModel.ADMIN or not payload.is_active):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate or demote your own account")

    removing_active_admin = (
        user.role == UserRoleModel.ADMIN
        and user.is_active
        and (payload.role != UserRoleModel.ADMIN or not payload.is_active)
    )
    if removing_active_admin:
        active_admins = await db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRoleModel.ADMIN,
                User.is_active.is_(True),
            )
        )
        if active_admins <= 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "At least one active admin account must remain")

    if payload.publisher_id is not None and await db.get(Publisher, payload.publisher_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publisher not found")
    if payload.advertiser_id is not None and await db.get(Advertiser, payload.advertiser_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Advertiser not found")

    user.role = UserRoleModel(payload.role.value)
    user.is_active = payload.is_active
    user.publisher_id = payload.publisher_id
    user.advertiser_id = payload.advertiser_id
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/ad-units/{ad_unit_id}/reports", summary="List visitor reports for an ad unit")
async def list_ad_unit_reports(
    ad_unit_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "staff")),
) -> list[dict[str, Any]]:
    ad_unit = await db.get(AdUnit, ad_unit_id)
    if ad_unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad unit not found")

    result = await db.execute(
        select(AdReport)
        .where(
            AdReport.ad_unit_id == ad_unit_id,
            AdReport.review_round == ad_unit.report_review_round,
        )
        .order_by(AdReport.created_at.desc())
    )
    return [
        {
            "id": report.id,
            "creative_id": report.creative_id,
            "reason": report.reason,
            "created_at": report.created_at,
        }
        for report in result.scalars().all()
    ]


class AdUnitActivation(BaseModel):
    is_active: bool


class AdUnitActivation(BaseModel):
    is_active: bool


@router.get(
    "/advertisers",
    response_model=list[AdvertiserOut],
    summary="List all advertisers for administration",
)
async def list_advertisers(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> list[Advertiser]:
    result = await db.execute(select(Advertiser).order_by(Advertiser.created_at.desc()))
    return list(result.scalars().all())


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
    if payload.status not in (PublisherStatus.ACTIVE, PublisherStatus.SUSPENDED, PublisherStatus.REJECTED):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review status must be active, suspended, or rejected")
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
    if payload.status not in (AccountStatus.ACTIVE, AccountStatus.SUSPENDED, AccountStatus.REJECTED):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Review status must be active, suspended, or rejected")
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
    ad_unit.report_review_round += 1
    ad_unit.rejection_reason = (
        payload.rejection_reason.strip() if payload.status == AdUnitStatus.REJECTED else None
    )
    await db.commit()
    await db.refresh(ad_unit)
    return ad_unit


@router.patch(
    "/ad-units/{ad_unit_id}/active",
    response_model=AdUnitOut,
    summary="Activate or deactivate an approved ad unit",
)
async def set_ad_unit_active(
    ad_unit_id: int,
    payload: AdUnitActivation,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> AdUnit:
    ad_unit = await db.get(AdUnit, ad_unit_id)
    if ad_unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad unit not found")
    if ad_unit.status != AdUnitStatus.APPROVED and payload.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only approved ad units can be activated")
    ad_unit.is_active = payload.is_active
    await db.commit()
    await db.refresh(ad_unit)
    return ad_unit


@router.patch(
    "/ad-units/{ad_unit_id}/active",
    response_model=AdUnitOut,
    summary="Activate or deactivate an approved ad unit",
)
async def set_ad_unit_active(
    ad_unit_id: int,
    payload: AdUnitActivation,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> AdUnit:
    ad_unit = await db.get(AdUnit, ad_unit_id)
    if ad_unit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ad unit not found")
    if ad_unit.status != AdUnitStatus.APPROVED and payload.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only approved ad units can be activated")
    ad_unit.is_active = payload.is_active
    await db.commit()
    await db.refresh(ad_unit)
    return ad_unit

@router.get("/events/recent", summary="Most recent tracking events (admin)")
async def recent_events(
    limit: int = Query(100, ge=1, le=500),
    after_id: int | None = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> list[dict[str, Any]]:
    stmt = (
        select(Event, Campaign.name, AdUnit.slot_name)
        .join(Campaign, Campaign.id == Event.campaign_id)
        .join(AdUnit, AdUnit.id == Event.ad_unit_id)
    )
    if after_id is not None:
        stmt = stmt.where(Event.id > after_id)
    rows = (await db.execute(stmt.order_by(Event.id.desc()).limit(limit))).all()
    return [
        {
            "id": e.id,
            "type": e.type.value,
            "campaign_id": e.campaign_id,
            "campaign_name": campaign_name,
            "ad_unit_id": e.ad_unit_id,
            "slot_name": slot_name,
            "creative_id": e.creative_id,
            "country_code": e.country_code,
            "cost": float(e.cost),
            "timestamp": e.timestamp.isoformat(),
        }
        for e, campaign_name, slot_name in rows
    ]