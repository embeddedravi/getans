from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field
    
class EventType(str, Enum):
    IMPRESSION = "impression"
    CLICK = "click"
    CONVERSION = "conversion"
    VIEWABLE_IMPRESSION = "viewable_impression"
    POLL_VOTE = "poll_vote"


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