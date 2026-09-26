from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Generic, TypeVar, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, PositiveInt

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

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXHAUSTED = "exhausted"
    ARCHIVED = "archived"


class BiddingStrategy(str, Enum):
    CPM = "cpm"
    CPC = "cpc"
    CPA = "cpa"


class TargetingRules(BaseModel):
    countries: list[str] | None = None
    device_types: list[str] | None = None
    keywords: list[str] | None = None

class CampaignCreate(BaseModel):
    advertiser_id: int
    name: str = Field(..., min_length=2, max_length=200)
    priority: int = Field(1, ge=1, le=100)
    bidding_strategy: BiddingStrategy = BiddingStrategy.CPM
    bid_amount: Decimal = Field(Decimal("1.0000"), gt=Decimal("0.0000"))
    daily_cap: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    total_budget: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    start_date: datetime
    end_date: Optional[datetime] = None
    targeting_rules: Optional[Dict[str, Any]] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    status: Optional[CampaignStatus] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=100)
    bid_amount: Optional[Decimal] = Field(None, gt=Decimal("0.0000"))
    daily_cap: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    total_budget: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    end_date: Optional[datetime] = None
    targeting_rules: Optional[Dict[str, Any]] = None


class CampaignOut(BaseModel):
    id: int
    advertiser_id: int
    name: str
    status: CampaignStatus
    is_active: bool
    priority: int
    bidding_strategy: BiddingStrategy
    bid_amount: Decimal
    daily_cap: Optional[Decimal] = None
    total_budget: Optional[Decimal] = None
    spent_amount: Decimal
    start_date: datetime
    end_date: Optional[datetime] = None
    targeting_rules: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
