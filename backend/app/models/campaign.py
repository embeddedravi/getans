from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Campaign(TimestampMixin, Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    advertiser_id: Mapped[int] = mapped_column(ForeignKey("advertisers.id"))
    name: Mapped[str] = mapped_column(String(200))

    is_active: Mapped[bool] = mapped_column(default=True)
    priority: Mapped[int] = mapped_column(default=1)  # higher wins ties

    daily_cap: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # See ad_selector._matches_targeting for the expected shape of this JSON.
    targeting_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    creatives: Mapped[list["Creative"]] = relationship(back_populates="campaign")
    advertiser: Mapped["Advertiser"] = relationship(back_populates="campaigns")
