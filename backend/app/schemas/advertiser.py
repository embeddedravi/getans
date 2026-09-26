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

class AccountStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class AdvertiserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    company_legal_name: Optional[str] = Field(None, max_length=255)
    billing_email: EmailStr
    website_url: Optional[HttpUrl] = None
    industry: Optional[str] = Field(None, max_length=100)
    currency: Currency = Currency.USD
    phone_number: Optional[str] = Field(None, max_length=32)
    vat_number: Optional[str] = Field(None, max_length=64)


class AdvertiserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    billing_email: Optional[EmailStr] = None
    website_url: Optional[HttpUrl] = None
    industry: Optional[str] = None
    status: Optional[AccountStatus] = None
    credit_limit: Optional[Decimal] = Field(None, ge=Decimal("0.00"))
    notes: Optional[str] = None


class AdvertiserOut(BaseModel):
    id: int
    name: str
    company_legal_name: Optional[str] = None
    billing_email: EmailStr
    website_url: Optional[str] = None
    industry: Optional[str] = None
    status: AccountStatus
    is_verified: bool
    currency: Currency
    balance: Decimal
    credit_limit: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)