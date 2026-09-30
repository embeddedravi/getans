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

class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    WIRE_TRANSFER = "wire_transfer"


class PayoutCreate(BaseModel):
    publisher_id: int
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    payment_method: Optional[PaymentMethod] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    notes: Optional[str] = None


class PayoutUpdate(BaseModel):
    status: Optional[PayoutStatus] = None
    reference: Optional[str] = Field(None, max_length=128)
    failure_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class PayoutOut(BaseModel):
    id: int
    publisher_id: int
    amount: Decimal
    status: PayoutStatus
    payment_method: Optional[PaymentMethod] = None
    payout_email: str
    reference: Optional[str] = None
    failure_reason: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
