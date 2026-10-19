from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.campaign import Campaign
from app.models.advertiser import Advertiser
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignOut, CampaignUpdate

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _apply_advertiser_scope(stmt, user: User):
    """Enforces multi-tenant data access controls for advertiser roles."""
    if user.role == "advertiser":
        return stmt.where(Campaign.advertiser_id == user.advertiser_id)
    return stmt


async def _get_owned_campaign(db: AsyncSession, campaign_id: int, user: User) -> Campaign:
    """Helper method to load and verify campaign permissions."""
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if user.role == "advertiser" and campaign.advertiser_id != user.advertiser_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to requested campaign",
        )
    return campaign


@router.post(
    "",
    response_model=CampaignOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new advertising campaign",
)
async def create_campaign(
    payload: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Campaign:
    """Creates a campaign tied to the current advertiser."""
    if user.role == "advertiser" and payload.advertiser_id != user.advertiser_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create campaigns for another advertiser account",
        )

    if payload.end_date and payload.end_date <= payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be set after start_date",
        )

    reservation = payload.total_budget or 0
    if reservation > 0:
        # Conditional UPDATE prevents concurrent campaign creations from
        # reserving more than the available wallet balance.
        result = await db.execute(
            update(Advertiser)
            .where(Advertiser.id == payload.advertiser_id, Advertiser.balance >= reservation)
            .values(balance=Advertiser.balance - reservation)
        )
        if result.rowcount != 1:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Insufficient available wallet balance for campaign budget",
            )

    campaign = Campaign(
        advertiser_id=payload.advertiser_id,
        name=payload.name,
        priority=payload.priority,
        bidding_strategy=payload.bidding_strategy,
        bid_amount=payload.bid_amount,
        daily_cap=payload.daily_cap,
        total_budget=payload.total_budget,
        reserved_amount=reservation,
        start_date=payload.start_date,
        end_date=payload.end_date,
        targeting_rules=payload.targeting_rules,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get(
    "",
    response_model=List[CampaignOut],
    summary="List available campaigns",
)
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> List[Campaign]:
    """Retrieves campaigns scoped to the user's account role."""
    stmt = _apply_advertiser_scope(select(Campaign), user).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/{campaign_id}",
    response_model=CampaignOut,
    summary="Get single campaign by ID",
)
async def get_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Campaign:
    """Loads details for a specific campaign ID."""
    return await _get_owned_campaign(db, campaign_id, user)


@router.patch(
    "/{campaign_id}",
    response_model=CampaignOut,
    summary="Update an existing campaign",
)
async def update_campaign(
    campaign_id: int,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Campaign:
    """Updates selected fields on a campaign."""
    campaign = await _get_owned_campaign(db, campaign_id, user)
    updates = payload.model_dump(exclude_unset=True)

    # Validate updated dates
    new_start = updates.get("start_date", campaign.start_date)
    new_end = updates.get("end_date", campaign.end_date)
    if new_end and new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be after start_date",
        )

    for field, value in updates.items():
        setattr(campaign, field, value)

    if "total_budget" in updates:
        old_budget = campaign.reserved_amount
        new_budget = updates["total_budget"] or 0
        if new_budget < campaign.spent_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="total_budget cannot be lower than campaign spend",
            )
        delta = new_budget - old_budget
        if delta > 0:
            result = await db.execute(
                update(Advertiser)
                .where(Advertiser.id == campaign.advertiser_id, Advertiser.balance >= delta)
                .values(balance=Advertiser.balance - delta)
            )
            if result.rowcount != 1:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Insufficient available wallet balance for increased campaign budget",
                )
        elif delta < 0:
            await db.execute(
                update(Advertiser)
                .where(Advertiser.id == campaign.advertiser_id)
                .values(balance=Advertiser.balance + abs(delta))
            )
        campaign.reserved_amount = new_budget

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a campaign",
)
async def delete_campaign(
    campaign_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> None:
    """Deletes a campaign and cascades associated records."""
    campaign = await _get_owned_campaign(db, campaign_id, user)
    refundable = max(campaign.reserved_amount - campaign.spent_amount, 0)
    if refundable:
        await db.execute(
            update(Advertiser)
            .where(Advertiser.id == campaign.advertiser_id)
            .values(balance=Advertiser.balance + refundable)
        )
    await db.delete(campaign)
    await db.commit()
