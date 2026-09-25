from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate

router = APIRouter()


def _scoped_to_advertiser(stmt, user: User):
    """Advertiser-role users only ever see their own campaigns."""
    if user.role == "advertiser":
        return stmt.where(Campaign.advertiser_id == user.advertiser_id)
    return stmt


@router.post(
    "",
    response_model=CampaignOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin", "advertiser"))],
)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Campaign:
    if user.role == "advertiser" and payload.advertiser_id != user.advertiser_id:
        raise HTTPException(status_code=403, detail="Cannot create campaigns for another advertiser")

    if payload.end_date <= payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    campaign = Campaign(
        advertiser_id=payload.advertiser_id,
        name=payload.name,
        priority=payload.priority,
        daily_cap=payload.daily_cap,
        start_date=payload.start_date,
        end_date=payload.end_date,
        targeting_rules=payload.targeting_rules.model_dump(exclude_none=True)
        if payload.targeting_rules
        else None,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_role("admin", "advertiser"))
) -> list[Campaign]:
    stmt = _scoped_to_advertiser(select(Campaign), user)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Campaign:
    campaign = await _get_owned_campaign(db, campaign_id, user)
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Campaign:
    campaign = await _get_owned_campaign(db, campaign_id, user)

    updates = payload.model_dump(exclude_unset=True)
    if "targeting_rules" in updates and updates["targeting_rules"] is not None:
        updates["targeting_rules"] = payload.targeting_rules.model_dump(exclude_none=True)

    for field, value in updates.items():
        setattr(campaign, field, value)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> None:
    campaign = await _get_owned_campaign(db, campaign_id, user)
    await db.delete(campaign)
    await db.commit()


async def _get_owned_campaign(db: AsyncSession, campaign_id: int, user: User) -> Campaign:
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if user.role == "advertiser" and campaign.advertiser_id != user.advertiser_id:
        raise HTTPException(status_code=403, detail="Not your campaign")
    return campaign
