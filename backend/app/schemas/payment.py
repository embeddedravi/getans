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


class AdvertiserTopUpOrderCreate(BaseModel):
    amount: Decimal = Field(..., ge=Decimal("1.00"), le=Decimal("500000.00"), decimal_places=2)


class AdvertiserTopUpOrderOut(BaseModel):
    order_id: str
    amount_paise: int
    currency: str = "INR"
    key_id: str
    advertiser_name: str
    billing_email: str


class AdvertiserTopUpVerify(BaseModel):
    razorpay_order_id: str = Field(..., min_length=8, max_length=64)
    razorpay_payment_id: str = Field(..., min_length=8, max_length=64)
    razorpay_signature: str = Field(..., min_length=32, max_length=128)


class AdvertiserWalletOut(BaseModel):
    balance: Decimal
    currency: str = "INR"
    credit_limit: Decimal


class AdvertiserTopUpVerifyOut(AdvertiserWalletOut):
    status: str = "paid"
    
