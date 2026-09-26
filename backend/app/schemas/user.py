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


# ============================================================================
# Auth & User Schemas
# ============================================================================


class UserRole(str, Enum):
    ADMIN = "admin"
    PUBLISHER = "publisher"
    ADVERTISER = "advertiser"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="User cleartext password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(3600, description="Token validity duration in seconds")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    role: UserRole
    publisher_id: Optional[int] = None
    advertiser_id: Optional[int] = None


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    publisher_id: Optional[int] = None
    advertiser_id: Optional[int] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
