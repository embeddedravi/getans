from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.ad_unit import AdUnit
from app.models.publisher import Publisher
from app.schemas.publisher import AdUnitCreate, AdUnitOut, PublisherCreate, PublisherOut

router = APIRouter()


@router.post(
    "",
    response_model=PublisherOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
async def create_publisher(payload: PublisherCreate, db: AsyncSession = Depends(get_db)) -> Publisher:
    publisher = Publisher(name=payload.name, site_url=payload.site_url)
    db.add(publisher)
    await db.commit()
    await db.refresh(publisher)
    return publisher


@router.get("", response_model=list[PublisherOut])
async def list_publishers(db: AsyncSession = Depends(get_db)) -> list[Publisher]:
    result = await db.execute(select(Publisher))
    return list(result.scalars().all())


@router.get("/{publisher_id}", response_model=PublisherOut)
async def get_publisher(publisher_id: int, db: AsyncSession = Depends(get_db)) -> Publisher:
    publisher = await db.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(status_code=404, detail="Publisher not found")
    return publisher


@router.post("/{publisher_id}/ad-units", response_model=AdUnitOut, status_code=status.HTTP_201_CREATED)
async def create_ad_unit(
    publisher_id: int, payload: AdUnitCreate, db: AsyncSession = Depends(get_db)
) -> AdUnit:
    if payload.publisher_id != publisher_id:
        raise HTTPException(status_code=400, detail="publisher_id mismatch")

    publisher = await db.get(Publisher, publisher_id)
    if publisher is None:
        raise HTTPException(status_code=404, detail="Publisher not found")

    ad_unit = AdUnit(
        publisher_id=publisher_id,
        slot_name=payload.slot_name,
        width=payload.width,
        height=payload.height,
    )
    db.add(ad_unit)
    await db.commit()
    await db.refresh(ad_unit)
    return ad_unit


@router.get("/{publisher_id}/ad-units", response_model=list[AdUnitOut])
async def list_ad_units(publisher_id: int, db: AsyncSession = Depends(get_db)) -> list[AdUnit]:
    result = await db.execute(select(AdUnit).where(AdUnit.publisher_id == publisher_id))
    return list(result.scalars().all())
