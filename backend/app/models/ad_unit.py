from __future__ import annotations

from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.publisher import Publisher


class AdFormatType(str, PyEnum):
    DISPLAY = "display"
    BANNER = "banner"
    NATIVE = "native"
    VIDEO = "video"
    INTERSTITIAL = "interstitial"


class AdUnit(TimestampMixin, Base):
    """A single ad slot on a publisher's site, e.g. 'sidebar-300x250'."""

    __tablename__ = "ad_units"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign Key
    publisher_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Slot Identity & Description
    slot_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Specification & Dimensions
    format_type: Mapped[AdFormatType] = mapped_column(
        Enum(AdFormatType, native_enum=False),
        default=AdFormatType.DISPLAY,
        nullable=False,
        index=True,
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    # Floor Price & Monetization Settings
    reserve_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=4),
        default=Decimal("0.0000"),
        nullable=False,
    )  # Minimum bid required (CPM floor price)

    # Status Flags & Delivery Controls
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    allow_house_ads: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Advanced Targeting & Configuration Payload (e.g., IAB categories, viewability rules)
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Relationships
    publisher: Mapped["Publisher"] = relationship(
        "Publisher",
        back_populates="ad_units",
        lazy="joined",
    )
    events: Mapped[List["Event"]] = relationship(
        "Event",
        back_populates="ad_unit",
        lazy="select",
    )

    # Constraints & Performance Indexes
    __table_args__ = (
        # Ensure slot names are unique per publisher
        UniqueConstraint("publisher_id", "slot_name", name="uq_publisher_slot_name"),
        CheckConstraint("width > 0 AND height > 0", name="check_positive_ad_unit_dimensions"),
        CheckConstraint("reserve_price >= 0.0000", name="check_positive_reserve_price"),
        # Compound index for fast ad matching engine queries
        Index(
            "ix_ad_units_matching_lookup",
            "is_active",
            "width",
            "height",
            "format_type",
        ),
    )

    @property
    def dimensions(self) -> str:
        """Returns string dimension representation (e.g., '300x250')."""
        return f"{self.width}x{self.height}"

    def __repr__(self) -> str:
        return f"<AdUnit(id={self.id}, publisher_id={self.publisher_id}, slot_name='{self.slot_name}', dimensions='{self.dimensions}')>"