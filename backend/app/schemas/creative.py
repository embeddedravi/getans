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
    POLL = "poll"


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
    poll_question: Optional[str] = Field(None, max_length=500)
    poll_options: Optional[List[str]] = None

    @model_validator(mode="after")
    def _has_source(self):
        if self.format == CreativeFormat.POLL:
            question = self.poll_question or (self.custom_attributes and self.custom_attributes.get("poll_question"))
            options = self.poll_options or (self.custom_attributes and self.custom_attributes.get("poll_options"))
            if not question or not isinstance(question, str) or not question.strip():
                raise ValueError("Poll ad requires 1 non-empty question")
            if not options or not isinstance(options, list) or len(options) != 4:
                raise ValueError("Poll ad requires exactly 4 options")
            clean_options = [str(opt).strip() for opt in options]
            if any(not opt for opt in clean_options):
                raise ValueError("All 4 poll options must be non-empty")

            if self.custom_attributes is None:
                self.custom_attributes = {}
            self.custom_attributes["poll_question"] = question.strip()
            self.custom_attributes["poll_options"] = clean_options

            if self.width is None:
                self.width = 300
            if self.height is None:
                self.height = 250
            if self.asset_url is None:
                self.asset_url = HttpUrl("https://poll.getans.local/banner.png")
            return self

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
    html_snippet: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    is_active: bool
    review_status: ReviewStatus
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PollResultsOut(BaseModel):
    creative_id: int
    question: str
    options: List[str]
    counts: List[int]
    percentages: List[float]
    total_votes: int

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