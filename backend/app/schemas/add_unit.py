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
    
class AdFormatType(str, Enum):
    DISPLAY = "display"
    BANNER = "banner"
    NATIVE = "native"
    VIDEO = "video"
    INTERSTITIAL = "interstitial"


class AdUnitCreate(BaseModel):
    publisher_id: int
    slot_name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=255)
    format_type: AdFormatType = AdFormatType.DISPLAY
    width: PositiveInt
    height: PositiveInt
    reserve_price: Decimal = Field(Decimal("0.0000"), ge=Decimal("0.0000"))
    allow_house_ads: bool = True
    settings: Optional[Dict[str, Any]] = None


class AdUnitOut(BaseModel):
    id: int
    publisher_id: int
    slot_name: str
    description: Optional[str] = None
    format_type: AdFormatType
    width: int
    height: int
    reserve_price: Decimal
    is_active: bool
    allow_house_ads: bool
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)