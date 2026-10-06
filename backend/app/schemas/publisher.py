from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Generic, TypeVar, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, PositiveInt, model_validator

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


class PublisherStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class PublisherCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    site_url: HttpUrl
    payout_email: EmailStr
    domain: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)


class PublisherUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    site_url: Optional[HttpUrl] = None
    payout_email: Optional[EmailStr] = None
    status: Optional[PublisherStatus] = None
    is_active: Optional[bool] = None
    revenue_share_percentage: Optional[Decimal] = Field(None, ge=Decimal("0.00"), le=Decimal("100.00"))


class PublisherOut(BaseModel):
    id: int
    name: str
    site_url: str
    domain: Optional[str] = None
    category: Optional[str] = None
    api_key: str
    status: PublisherStatus
    is_active: bool
    ads_txt_verified: bool
    revenue_share_percentage: Decimal
    unpaid_earnings: Decimal
    payout_email: EmailStr
    rejection_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PublisherReview(BaseModel):
    status: PublisherStatus
    rejection_reason: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def _reason_required_on_reject(self):
        if self.status == PublisherStatus.REJECTED and not (self.rejection_reason or "").strip():
            raise ValueError("rejection_reason is required when rejecting a publisher")
        return self
