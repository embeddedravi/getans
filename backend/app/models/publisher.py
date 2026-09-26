from __future__ import annotations

from decimal import Decimal
from enum import Enum as PyEnum
import secrets
from typing import TYPE_CHECKING, List, Optional

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ad_unit import AdUnit
    from app.models.payment import Payout
    from app.models.user import User


def _generate_api_key() -> str:
    return f"pub_live_{secrets.token_urlsafe(32)}"


class PublisherStatus(str, PyEnum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class PaymentMethod(str, PyEnum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    WIRE_TRANSFER = "wire_transfer"


class Publisher(TimestampMixin, Base):
    __tablename__ = "publishers"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Site & Organization Info
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    site_url: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # API Security & Authentication
    api_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        default=_generate_api_key,
        nullable=False,
    )

    # Account Status & Compliance
    status: Mapped[PublisherStatus] = mapped_column(
        Enum(PublisherStatus, native_enum=False),
        default=PublisherStatus.PENDING_APPROVAL,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ads_txt_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Revenue & Financial Configuration
    revenue_share_percentage: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=2),
        default=Decimal("70.00"),  # Standard 70/30 network split
        nullable=False,
    )
    unpaid_earnings: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Payment Information
    payout_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod, native_enum=False),
        nullable=True,
    )

    # Operational Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    ad_units: Mapped[List["AdUnit"]] = relationship(
        "AdUnit",
        back_populates="publisher",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="publisher",
        lazy="selectin",
    )
    payouts: Mapped[List["Payout"]] = relationship(
        "Payout",
        back_populates="publisher",
        lazy="select",
    )

    # Constraints & Indexes
    __table_args__ = (
        CheckConstraint(
            "revenue_share_percentage >= 0.00 AND revenue_share_percentage <= 100.00",
            name="check_valid_rev_share",
        ),
        CheckConstraint("unpaid_earnings >= 0.00", name="check_positive_earnings"),
        Index("ix_publishers_status_active", "status", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Publisher(id={self.id}, name='{self.name}', status='{self.status.value}')>"