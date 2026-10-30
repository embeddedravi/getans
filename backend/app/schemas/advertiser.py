from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator

class AccountStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class Currency(str, Enum):
    INR = "INR"


class AdvertiserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    company_legal_name: Optional[str] = Field(None, max_length=255)
    billing_email: EmailStr
    website_url: Optional[HttpUrl] = None
    industry: Optional[str] = Field(None, max_length=100)
    currency: Currency = Currency.INR
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
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdvertiserReview(BaseModel):
    status: AccountStatus
    rejection_reason: Optional[str] = Field(None, max_length=500)

    @model_validator(mode="after")
    def _reason_required_on_reject(self):
        if self.status == AccountStatus.REJECTED and not (self.rejection_reason or "").strip():
            raise ValueError("rejection_reason is required when rejecting an advertiser")
        return self
