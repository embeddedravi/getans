"""Historical analytics endpoints (REST). Live counters are pushed separately
via the /dashboard Socket.IO namespace -- these endpoints back the charts
that need a date range rather than a live tick.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.campaign import Campaign
from app.models.event import Event
from app.models.user import User
from pydantic import BaseModel

router = APIRouter()


class CampaignStats(BaseModel):
    campaign_id: int
    campaign_name: str
    impressions: int
    clicks: int
    ctr: float


@router.get("/campaigns", response_model=list[CampaignStats])
async def campaign_stats(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> list[CampaignStats]:
    stmt = (
        select(
            Campaign.id,
            Campaign.name,
            func.count(Event.id).filter(Event.type == "impression").label("impressions"),
            func.count(Event.id).filter(Event.type == "click").label("clicks"),
        )
        .join(Event, Event.campaign_id == Campaign.id)
        .where(Event.timestamp >= start, Event.timestamp <= end)
        .group_by(Campaign.id, Campaign.name)
    )

    if user.role == "advertiser":
        stmt = stmt.where(Campaign.advertiser_id == user.advertiser_id)

    result = await db.execute(stmt)

    stats = []
    for campaign_id, name, impressions, clicks in result.all():
        ctr = (clicks / impressions * 100) if impressions else 0.0
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
