from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Generic, TypeVar, Optional
from pydantic import BaseModel, ConfigDict, model_validator, EmailStr, Field, HttpUrl, PositiveInt

# ============================================================================
# Generic / Shared Schemas
# ============================================================================

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard container for paginated list endpoints."""

    items: List[T]
    total: int = Field(..., ge=0, description="Total matching records count")
    page: int = Field(1, ge=1, description="Current page number")
    size: int = Field(50, ge=1, le=100, description="Items per page")
    pages: int = Field(..., ge=0, description="Total pages count")


class MessageResponse(BaseModel):
    """Standard message response for operations without payload return."""

    message: str


class CreativeFormat(str, Enum):
    IMAGE = "image"
    HTML = "html"
    VIDEO = "video"
    NATIVE = "native"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CreativeCreate(BaseModel):
    campaign_id: int
    media_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=200)
    asset_url: Optional[HttpUrl] = None
    click_url: HttpUrl
    impression_tracker_url: Optional[HttpUrl] = None
    format: CreativeFormat = CreativeFormat.IMAGE
    width: Optional[PositiveInt] = None
    height: Optional[PositiveInt] = None
    html_snippet: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _has_source(self):
        if self.media_id is None and not (self.asset_url and self.width and self.height):
            raise ValueError("Provide media_id, or asset_url with width and height")
        return self


class CreativeOut(BaseModel):
    id: int
    campaign_id: int
    media_asset_id: Optional[int] = None
    name: Optional[str] = None
    asset_url: str
    click_url: str
    impression_tracker_url: Optional[str] = None
    format: CreativeFormat
    width: int
    height: int
    is_active: bool
    review_status: ReviewStatus
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CreativeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class CreativeReview(BaseModel):
    review_status: ReviewStatus
    rejection_reason: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def _reason_required_on_reject(self):
        if self.review_status == ReviewStatus.REJECTED and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting a creative")
        return self