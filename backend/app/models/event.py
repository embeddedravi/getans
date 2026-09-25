from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Event(Base):
    """An impression or click, used for analytics and budget tracking."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad_unit_id: Mapped[int] = mapped_column(ForeignKey("ad_units.id"))
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))
    creative_id: Mapped[int] = mapped_column(ForeignKey("creatives.id"))

    type: Mapped[str] = mapped_column(String(20))  # "impression" | "click"
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
