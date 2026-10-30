from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.campaign import Campaign
from app.models.creative import Creative, ReviewStatus, CreativeFormat
from app.models.user import User

from app.models.media_asset import MediaKind, MediaAsset
from app.schemas.generic import PaginatedResponse
from app.schemas.creative import CreativeCreate, CreativeOut, CreativeUpdate, CreativeReview, PollResultsOut
from app.models.event import Event, EventType

router = APIRouter(prefix="/creatives", tags=["Creatives"])


@router.get("/polls", summary="List poll creatives visible to the current advertiser or admin")
async def list_poll_creatives(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[dict]:
    # 1. Base query for filtering
    base_query = (
        select(Creative, Campaign)
        .join(Campaign, Campaign.id == Creative.campaign_id)
        .where(Creative.format == CreativeFormat.POLL)
    )
    if user.role == "advertiser":
        base_query = base_query.where(Campaign.advertiser_id == user.advertiser_id)

    # 2. Get the total count of matching records
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar_one()

    # 3. Calculate total pages
    pages = (total + size - 1) // size if total > 0 else 0

    # 4. Apply sorting, pagination (limit/offset), and execute
    paginated_query = (
        base_query
        .order_by(Creative.created_at.desc(), Creative.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    rows = (await db.execute(paginated_query)).all()

    # 5. Format items
    items = [
        {
            "creative": CreativeOut.model_validate(creative).model_dump(mode="json"),
            "campaign": {"id": campaign.id, "name": campaign.name},
        }
        for creative, campaign in rows
    ]

    # 6. Return the paginated structure
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post(
    "",
    response_model=CreativeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new creative asset",
)
async def create_creative(
    payload: CreativeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Creative:
    """Attaches a new ad creative asset to a specified campaign."""
    campaign = await db.get(Campaign, payload.campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent campaign not found",
        )
    if user.role == "advertiser" and campaign.advertiser_id != user.advertiser_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot add creatives to a campaign owned by another advertiser",
        )

    asset_url, width, height, fmt = payload.asset_url, payload.width, payload.height, payload.format
    media_asset_id = None
    if payload.media_id is not None:
        asset = await db.get(MediaAsset, payload.media_id)
        if asset is None or asset.advertiser_id != campaign.advertiser_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Media asset not found")
        asset_url, width, height = asset.url, asset.width, asset.height
        fmt = CreativeFormat.VIDEO if asset.kind == MediaKind.VIDEO else CreativeFormat.IMAGE
        media_asset_id = asset.id

    creative = Creative(
        campaign_id=payload.campaign_id,
        media_asset_id=media_asset_id,
        name=payload.name,
        asset_url=str(asset_url),
        click_url=str(payload.click_url),
        impression_tracker_url=str(payload.impression_tracker_url) if payload.impression_tracker_url else None,
        format=fmt,
        width=width,
        height=height,
        html_snippet=payload.html_snippet,
        custom_attributes=payload.custom_attributes,
    )
    db.add(creative)
    await db.commit()
    await db.refresh(creative)
    return creative


@router.get(
    "/by-campaign/{campaign_id}",
    response_model=PaginatedResponse[CreativeOut],
    summary="List creatives by campaign",
)
async def list_creatives_for_campaign(
    campaign_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> PaginatedResponse[CreativeOut]:
    """Retrieves all creatives belonging to a given campaign ID."""
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if user.role == "advertiser" and campaign.advertiser_id != user.advertiser_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to campaign creatives",
        )

    stmt = select(Creative).where(Creative.campaign_id == campaign_id).order_by(Creative.created_at.desc(), Creative.id.desc())
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    result = await db.execute(stmt.offset((page - 1) * size).limit(size))
    return PaginatedResponse(items=list(result.scalars().all()), total=total, page=page, size=size, pages=(total + size - 1) // size)


@router.delete(
    "/{creative_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a creative asset",
)
async def delete_creative(
    creative_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> None:
    """Removes a creative asset from the database."""
    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Creative asset not found",
        )

    campaign = await db.get(Campaign, creative.campaign_id)
    if user.role == "advertiser" and (campaign is None or campaign.advertiser_id != user.advertiser_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to requested creative asset",
        )

    await db.delete(creative)
    await db.commit()

async def _get_owned_creative(db: AsyncSession, creative_id: int, user: User) -> Creative:
    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creative asset not found")
    campaign = await db.get(Campaign, creative.campaign_id)
    if user.role == "advertiser" and (campaign is None or campaign.advertiser_id != user.advertiser_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied to requested creative asset")
    return creative


@router.patch("/{creative_id}", response_model=CreativeOut, summary="Update a creative")
async def update_creative(
    creative_id: int,
    payload: CreativeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> Creative:
    creative = await _get_owned_creative(db, creative_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(creative, field, value)
    await db.commit()
    await db.refresh(creative)
    return creative


@router.patch("/{creative_id}/review", response_model=CreativeOut, summary="Approve or reject a creative")
async def review_creative(
    creative_id: int,
    payload: CreativeReview,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> Creative:
    creative = await db.get(Creative, creative_id)
    if creative is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Creative asset not found")
    creative.review_status = payload.review_status
    creative.rejection_reason = (
        payload.rejection_reason if payload.review_status == ReviewStatus.REJECTED else None
    )
    await db.commit()
    await db.refresh(creative)
    return creative


@router.get("/{creative_id}/poll-results", response_model=PollResultsOut, summary="Get poll voting results")
async def get_poll_results(
    creative_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> PollResultsOut:
    creative = await _get_owned_creative(db, creative_id, user)
    if creative.format != CreativeFormat.POLL:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Creative is not a poll ad")

    attrs = creative.custom_attributes or {}
    question = attrs.get("poll_question", "Poll")
    options = attrs.get("poll_options", ["Option 1", "Option 2", "Option 3", "Option 4"])

    result = await db.execute(
        select(Event.meta)
        .where(
            Event.creative_id == creative_id,
            Event.type == EventType.POLL_VOTE,
            Event.is_valid.is_(True),
        )
    )
    counts = [0, 0, 0, 0]
    for row in result.scalars():
        if isinstance(row, dict) and "option_index" in row:
            try:
                idx = int(row["option_index"])
                if 0 <= idx < 4:
                    counts[idx] += 1
            except (ValueError, TypeError):
                pass
    total = sum(counts)
    percentages = [round((c / total * 100), 1) if total > 0 else 0.0 for c in counts]

    return PollResultsOut(
        creative_id=creative_id,
        question=question,
        options=options,
        counts=counts,
        percentages=percentages,
        total_votes=total,
    )
