from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Creative(TimestampMixin, Base):
    """A specific ad asset belonging to a campaign, sized for one ad unit shape."""

    __tablename__ = "creatives"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("campaigns.id"))

    asset_url: Mapped[str] = mapped_column(String(1000))
    click_url: Mapped[str] = mapped_column(String(1000))
    format: Mapped[str] = mapped_column(String(20), default="image")  # image | html | video

    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()

    campaign: Mapped["Campaign"] = relationship(back_populates="creatives")
