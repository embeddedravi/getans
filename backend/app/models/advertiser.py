from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, List, Optional
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    Index,
    Numeric,
    String,
    Text,
)


if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.user import User


class AccountStatus(str, PyEnum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class Currency(str, PyEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class Advertiser(TimestampMixin, Base):
    __tablename__ = "advertisers"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Core Business Info
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    company_legal_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # Status & Flags
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False),
        default=AccountStatus.PENDING_VERIFICATION,
        nullable=False,
        index=True,
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Contact & Billing Details
    billing_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    vat_number: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Financial & Credit Configuration
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, native_enum=False),
        default=Currency.USD,
        nullable=False,
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Metadata / Operational Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    campaigns: Mapped[List["Campaign"]] = relationship(
        "Campaign",
        back_populates="advertiser",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="advertiser",
        lazy="selectin",
    )

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint("balance >= 0.00", name="check_positive_balance"),
        CheckConstraint("credit_limit >= 0.00", name="check_positive_credit_limit"),
        Index("ix_advertisers_status_created", "status", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Advertiser(id={self.id}, name='{self.name}', status='{self.status.value}')>"
