from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    JSON
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ad_unit import AdUnit
    from app.models.campaign import Campaign
    from app.models.creative import Creative


class EventType(str, PyEnum):
    IMPRESSION = "impression"
    CLICK = "click"
    CONVERSION = "conversion"
    VIEWABLE_IMPRESSION = "viewable_impression"


class Event(Base):
    """An impression, click, or conversion event used for real-time analytics, billable event processing, and fraud detection."""

    __tablename__ = "events"

    # Primary Key - BigInteger for high-cardinality event stream tables
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Unique Event Identifier for Deduplication (e.g., UUIDv4)
    event_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        unique=True,
        nullable=True,
        index=True,
    )

    # Foreign Keys to Ad Serving Entities
    ad_unit_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ad_units.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    creative_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("creatives.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event Attributes & Classification
    type: Mapped[EventType] = mapped_column(
        Enum(EventType, native_enum=False),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Financial & Cost Attribution
    cost: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        default=Decimal("0.000000"),
        nullable=False,
    )  # Micro-costs per event (CPM/CPC/CPA)

    # Fraud & Validity Tracking
    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )  # False if flagged by anti-fraud filter (bot traffic, click farming)

    # Contextual Client Info (Useful for fast OLAP/attribution queries)
    user_ip: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True, index=True)

    # Extensible Metadata (Geo, Device, Ref Headers, Viewability metrics)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    ad_unit: Mapped["AdUnit"] = relationship("AdUnit", lazy="select")
    campaign: Mapped["Campaign"] = relationship("Campaign", lazy="select")
    creative: Mapped["Creative"] = relationship("Creative", lazy="select")

    # Composite Indexes for Analytics & Aggregation Pipelines
    __table_args__ = (
        CheckConstraint("cost >= 0.000000", name="check_positive_event_cost"),
        # Index for time-range reporting per campaign
        Index("ix_events_campaign_time", "campaign_id", "type", "timestamp"),
        # Index for time-range reporting per ad unit (publisher payouts)
        Index("ix_events_ad_unit_time", "ad_unit_id", "type", "timestamp"),
        # Composite index for fraud/analytics processing
        Index("ix_events_type_valid_time", "type", "is_valid", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, type='{self.type.value}', campaign_id={self.campaign_id}, valid={self.is_valid})>"