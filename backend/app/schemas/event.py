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
    
class EventType(str, Enum):
    IMPRESSION = "impression"
    CLICK = "click"
    CONVERSION = "conversion"
    VIEWABLE_IMPRESSION = "viewable_impression"


class EventIngest(BaseModel):
    """Schema for incoming ad event tracking payloads."""

    event_id: Optional[str] = Field(None, description="Client-supplied UUID for deduplication")
    ad_unit_id: int
    campaign_id: int
    creative_id: int
    type: EventType
    cost: Decimal = Field(Decimal("0.000000"), ge=Decimal("0.000000"))
    user_agent: Optional[str] = Field(None, max_length=512)
    meta: Optional[Dict[str, Any]] = None


class EventOut(BaseModel):
    id: int
    event_id: Optional[str] = None
    ad_unit_id: int
    campaign_id: int
    creative_id: int
    type: EventType
    timestamp: datetime
    cost: Decimal
    is_valid: bool
    country_code: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)