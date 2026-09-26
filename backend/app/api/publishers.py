from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.ad_unit import AdUnit
from app.models.publisher import Publisher
from app.models.user import User
from app.schemas.publisher import PublisherCreate, PublisherOut
from app.schemas.add_unit import AdUnitCreate, AdUnitOut

router = APIRouter(prefix="/publishers", tags=["Publishers & Ad Units"])


@router.post(
    "",
    response_model=PublisherOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new publisher account",
)
async def create_publisher(
    payload: PublisherCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> Publisher:
    """Creates a new publisher account (Admin restricted)."""
    publisher = Publisher(
        name=payload.name,
        site_url=str(payload.site_url),
        payout_email=payload.payout_email,
        domain=payload.domain,
        category=payload.category,
    )
    db.add(publisher)
    await db.commit()
    await db.refresh(publisher)
    return publisher


@router.get(
    "",
    response_model=List[PublisherOut],
    summary="List registered publishers",
)
async def list_publishers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> List[Publisher]:
    """Lists registered publishers according to permission context."""
    stmt = select(Publisher)
    if user.role == "publisher":
        stmt = stmt.where(Publisher.id == user.publisher_id)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{publisher_id}",
    response_model=PublisherOut,
    summary="Get publisher details by ID",
)
async def get_publisher(
    publisher_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> Publisher:
    """Retrieves details of a specified publisher."""
    if user.role == "publisher" and user.publisher_id != publisher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to requested publisher details",
        )

    publisher = await db.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )
    return publisher


@router.post(
    "/{publisher_id}/ad-units",
    response_model=AdUnitOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new ad unit slot",
)
async def create_ad_unit(
    publisher_id: int,
    payload: AdUnitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> AdUnit:
    """Creates a new ad unit under a publisher account."""
    if user.role == "publisher" and user.publisher_id != publisher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add ad units to another publisher account",
        )

    if payload.publisher_id != publisher_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path parameter publisher_id does not match request payload publisher_id",
        )

    publisher = await db.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    ad_unit = AdUnit(
        publisher_id=publisher_id,
        slot_name=payload.slot_name,
        description=payload.description,
        format_type=payload.format_type,
        width=payload.width,
        height=payload.height,
        reserve_price=payload.reserve_price,
        allow_house_ads=payload.allow_house_ads,
        settings=payload.settings,
    )
    db.add(ad_unit)
    await db.commit()
    await db.refresh(ad_unit)
    return ad_unit


@router.get(
    "/{publisher_id}/ad-units",
    response_model=List[AdUnitOut],
    summary="List ad units for a publisher",
)
async def list_ad_units(
    publisher_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> List[AdUnit]:
    """Fetches all ad placement units registered under a given publisher."""
    if user.role == "publisher" and user.publisher_id != publisher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to ad units",
        )

    result = await db.execute(select(AdUnit).where(AdUnit.publisher_id == publisher_id))
    return list(result.scalars().all())