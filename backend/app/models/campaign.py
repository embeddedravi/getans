from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.advertiser import Advertiser
    from app.models.creative import Creative


class CampaignStatus(str, PyEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXHAUSTED = "exhausted"  # Total budget/cap depleted
    ARCHIVED = "archived"


class BiddingStrategy(str, PyEnum):
    CPM = "cpm"  # Cost Per Mille (Impressions)
    CPC = "cpc"  # Cost Per Click
    CPA = "cpa"  # Cost Per Action/Conversion


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Organization Mapping
    advertiser_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("advertisers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Campaign Metadata
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, native_enum=False),
        default=CampaignStatus.DRAFT,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # Higher wins ties

    # Scheduling & Delivery Window
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Budgeting & Bidding Dynamics
    bidding_strategy: Mapped[BiddingStrategy] = mapped_column(
        Enum(BiddingStrategy, native_enum=False),
        default=BiddingStrategy.CPM,
        nullable=False,
    )
    bid_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=4),
        default=Decimal("1.0000"),
        nullable=False,
    )
    daily_cap: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True,
    )
    total_budget: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=12, scale=2),
        nullable=True,
    )
    spent_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=12, scale=2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Pacing & Targeting Rules
    # Note: JSONB is used for efficient indexing and querying under PostgreSQL
    targeting_rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )

    # Relationships
    advertiser: Mapped["Advertiser"] = relationship(
        "Advertiser",
        back_populates="campaigns",
        lazy="joined",
    )
    creatives: Mapped[List["Creative"]] = relationship(
        "Creative",
        back_populates="campaign",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints & Performance Indexes
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date > start_date", name="check_valid_date_range"),
        CheckConstraint("priority >= 1 AND priority <= 100", name="check_valid_priority_range"),
        CheckConstraint("bid_amount > 0.0000", name="check_positive_bid_amount"),
        CheckConstraint("daily_cap IS NULL OR daily_cap >= 0.00", name="check_positive_daily_cap"),
        CheckConstraint("total_budget IS NULL OR total_budget >= 0.00", name="check_positive_total_budget"),
        # Compound index for hot-path ad decision engine queries
        Index(
            "ix_campaigns_ad_server_lookup",
            "is_active",
            "status",
            "start_date",
            "end_date",
            "priority",
        ),
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status.value}', priority={self.priority})>"