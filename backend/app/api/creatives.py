from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.campaign import Campaign
from app.models.creative import Creative
from app.models.user import User
from app.schemas.creative import CreativeCreate, CreativeOut

router = APIRouter()


@router.post(
    "",
    response_model=CreativeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "advertiser"))],
)
async def create_creative(
    payload: CreativeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Creative:
    campaign = await db.get(Campaign, payload.campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if user.role == "advertiser" and campaign.advertiser_id != user.advertiser_id:
        raise HTTPException(status_code=403, detail="Not your campaign")

    creative = Creative(
        campaign_id=payload.campaign_id,
        asset_url=payload.asset_url,
        click_url=payload.click_url,
        format=payload.format,
        width=payload.width,
        height=payload.height,
    )
    db.add(creative)
    await db.commit()
    await db.refresh(creative)
    return creative


@router.get("/by-campaign/{campaign_id}", response_model=list[CreativeOut])
async def list_creatives_for_campaign(
    campaign_id: int, db: AsyncSession = Depends(get_db)
) -> list[Creative]:
    result = await db.execute(select(Creative).where(Creative.campaign_id == campaign_id))
    return list(result.scalars().all())


@router.delete("/{creative_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_creative(
    creative_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> None:
    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise HTTPException(status_code=404, detail="Creative not found")

    campaign = await db.get(Campaign, creative.campaign_id)
    if user.role == "advertiser" and campaign.advertiser_id != user.advertiser_id:
        raise HTTPException(status_code=403, detail="Not your creative")

    await db.delete(creative)
    await db.commit()
