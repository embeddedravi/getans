from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.ad_unit import AdUnit, AdUnitStatus
from app.models.publisher import Publisher, PublisherStatus
from app.models.user import User
from app.schemas.publisher import PublisherCreate, PublisherOut
from app.schemas.add_unit import AdUnitCreate, AdUnitOut
from app.schemas.generic import PaginatedResponse

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
    response_model=PaginatedResponse[PublisherOut],
    summary="List registered publishers",
)
async def list_publishers(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> PaginatedResponse[PublisherOut]:
    
    """Lists registered publishers according to permission context."""
    stmt = select(Publisher)
    if user.role == "publisher":
        stmt = stmt.where(Publisher.id == user.publisher_id)

    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    result = await db.execute(stmt.order_by(Publisher.id).offset((page - 1) * size).limit(size))
    return PaginatedResponse(
        items=list(result.scalars().all()), 
        total=total, 
        page=page, 
        size=size, 
        pages=(total + size - 1) // size
    )


@router.get(
    "/available-ad-units",
    summary="List approved active publisher inventory for advertisers",
)
async def available_ad_units(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("advertiser")),
) -> list[dict]:
    
    stmt = (
        select(AdUnit, Publisher)
        .join(Publisher, Publisher.id == AdUnit.publisher_id)
        .where(
            Publisher.status == PublisherStatus.ACTIVE,
            Publisher.is_active.is_(True),
            AdUnit.status == AdUnitStatus.APPROVED,
            AdUnit.is_active.is_(True),
        )
        .order_by(Publisher.name, AdUnit.slot_name)
    )
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = (await db.execute(stmt.offset((page - 1) * size).limit(size))).all()
    items = [
        {
            "id": unit.id,
            "publisher_id": publisher.id,
            "publisher_name": publisher.name,
            "site_url": publisher.site_url,
            "domain": publisher.domain,
            "category": publisher.category,
            "slot_name": unit.slot_name,
            "description": unit.description,
            "format_type": unit.format_type.value,
            "width": unit.width,
            "height": unit.height,
            "reserve_price": float(unit.reserve_price),
        }
        for unit, publisher in rows
    ]
    return PaginatedResponse(
        items=items, 
        total=total, 
        page=page, 
        size=size, 
        pages=(total + size - 1) // size
    )


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
    response_model=PaginatedResponse[AdUnitOut],
    summary="List ad units for a publisher",
)
async def list_ad_units(
    publisher_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> PaginatedResponse[AdUnitOut]:
    
    """Fetches all ad placement units registered under a given publisher."""
    if user.role == "publisher" and user.publisher_id != publisher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to ad units",
        )

    stmt = select(AdUnit).where(AdUnit.publisher_id == publisher_id).order_by(AdUnit.id)
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    result = await db.execute(stmt.offset((page - 1) * size).limit(size))
    return PaginatedResponse(
        items=list(result.scalars().all()), 
        total=total, 
        page=page, 
        size=size, 
        pages=(total + size - 1) // size
    )
