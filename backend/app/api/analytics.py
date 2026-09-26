"""Historical analytics endpoints (REST).

Live counters are pushed separately via the /dashboard Socket.IO namespace -- 
these endpoints back the charts that need a date range rather than a live tick.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.campaign import Campaign
from app.models.event import Event, EventType
from app.models.user import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class CampaignStats(BaseModel):
    campaign_id: int
    campaign_name: str
    impressions: int = Field(..., ge=0, description="Total impression count")
    clicks: int = Field(..., ge=0, description="Total click count")
    ctr: float = Field(..., ge=0.0, le=100.0, description="Click-Through Rate percentage")

    model_config = ConfigDict(from_attributes=True)


@router.get(
    "/campaigns",
    response_model=List[CampaignStats],
    summary="Get Campaign Performance Analytics",
)
async def campaign_stats(
    start: datetime = Query(..., description="Start range timestamp (UTC)"),
    end: datetime = Query(..., description="End range timestamp (UTC)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> List[CampaignStats]:
    """Retrieves aggregated impression, click, and CTR metrics for campaigns within a timeframe."""
    stmt = (
        select(
            Campaign.id,
            Campaign.name,
            func.coalesce(
                func.sum(
                    case((Event.type == EventType.IMPRESSION, 1), else_=0)
                ),
                0,
            ).label("impressions"),
            func.coalesce(
                func.sum(
                    case((Event.type == EventType.CLICK, 1), else_=0)
                ),
                0,
            ).label("clicks"),
        )
        .join(Event, Event.campaign_id == Campaign.id)
        .where(Event.timestamp >= start, Event.timestamp <= end)
        .group_by(Campaign.id, Campaign.name)
    )

    if user.role == "advertiser":
        stmt = stmt.where(Campaign.advertiser_id == user.advertiser_id)

    result = await db.execute(stmt)

    stats: List[CampaignStats] = []
    for campaign_id, name, impressions, clicks in result.all():
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
        stats.append(
            CampaignStats(
                campaign_id=campaign_id,
                campaign_name=name,
                impressions=impressions,
                clicks=clicks,
                ctr=round(ctr, 2),
            )
        )
    return stats