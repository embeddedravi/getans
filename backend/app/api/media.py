from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.creative import Creative
from app.models.media_asset import MediaAsset
from app.models.user import User
from app.schemas.media import MediaAssetOut
from app.services import media_storage
from app.schemas.generic import PaginatedResponse

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("", response_model=MediaAssetOut, status_code=status.HTTP_201_CREATED,
             summary="Upload an image or video to the media library")
async def upload_media(
    file: UploadFile = File(...),
    width: Optional[int] = Form(None, gt=0),    # only used for video if ffprobe isn't installed
    height: Optional[int] = Form(None, gt=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser")),
) -> MediaAsset:
    
    stored = await media_storage.save_upload(file, (width, height))
    asset = MediaAsset(
        advertiser_id=user.advertiser_id,
        kind=stored.kind,
        original_filename=(file.filename or "upload")[:255],
        stored_name=stored.stored_name,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        width=stored.width,
        height=stored.height,
        duration_seconds=stored.duration,
    )
    db.add(asset)
    try:
        await db.commit()
    except Exception:
        media_storage.delete_file(stored.stored_name)
        raise
    await db.refresh(asset)
    return asset


@router.get("", response_model=PaginatedResponse[MediaAssetOut], summary="List media assets")
async def list_media(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> PaginatedResponse[MediaAssetOut]:
    
    stmt = select(MediaAsset).order_by(MediaAsset.id.desc())
    if user.role == "advertiser":
        stmt = stmt.where(MediaAsset.advertiser_id == user.advertiser_id)
    total = await db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    result = await db.execute(stmt.offset((page - 1) * size).limit(size))
    return PaginatedResponse(
        items=list(result.scalars().all()), 
        total=total, 
        page=page, 
        size=size, 
        pages=(total + size - 1) // size
    )


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a media asset")
async def delete_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "advertiser")),
) -> None:
    
    asset = await db.get(MediaAsset, media_id)
    if asset is None or (user.role == "advertiser" and asset.advertiser_id != user.advertiser_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Media asset not found")
    in_use = await db.scalar(
        select(func.count(Creative.id)).where(Creative.media_asset_id == media_id)
    )
    if in_use:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Used by {in_use} creative(s). Delete those creatives first.",
        )
    name = asset.stored_name
    await db.delete(asset)
    await db.commit()
    media_storage.delete_file(name)
