from __future__ import annotations

from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.campaign import Campaign


class CreativeFormat(str, PyEnum):
    IMAGE = "image"
    HTML = "html"
    VIDEO = "video"
    NATIVE = "native"


class ReviewStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Creative(TimestampMixin, Base):
    """A specific ad asset belonging to a campaign, sized for one ad unit shape."""

    __tablename__ = "creatives"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Campaign Mapping
    campaign_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core Asset Meta & URLs
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    asset_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    click_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    impression_tracker_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    # Ad Specifications & Dimensions
    format: Mapped[CreativeFormat] = mapped_column(
        Enum(CreativeFormat, native_enum=False),
        default=CreativeFormat.IMAGE,
        nullable=False,
        index=True,
    )
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    # Rich Text / Native Payload (for HTML snippets or VAST/Native JSON payloads)
    html_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_attributes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)

    # Status, Security & Verification
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, native_enum=False),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Performance Caching Optimization
    weight: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False
    )  # Asset delivery weight for A/B testing

    # Relationships
    campaign: Mapped["Campaign"] = relationship(
        "Campaign",
        back_populates="creatives",
        lazy="joined",
    )

    # Constraints & Performance Indexes
    __table_args__ = (
        CheckConstraint("width > 0 AND height > 0", name="check_positive_dimensions"),
        CheckConstraint("weight >= 0 AND weight <= 1000", name="check_valid_creative_weight"),
        # Index tailored for rapid lookup during ad matching/selection
        Index("ix_creatives_ad_matching", "campaign_id", "is_active", "review_status", "width", "height"),
    )

    @property
    def dimensions(self) -> str:
        """Returns string dimension representation (e.g., '300x250')."""
        return f"{self.width}x{self.height}"

    def __repr__(self) -> str:
        return f"<Creative(id={self.id}, format='{self.format.value}', dimensions='{self.dimensions}', status='{self.review_status.value}')>"