from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class AdUnit(TimestampMixin, Base):
    """A single ad slot on a publisher's site, e.g. 'sidebar-300x250'."""

    __tablename__ = "ad_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    publisher_id: Mapped[int] = mapped_column(ForeignKey("publishers.id"))
    slot_name: Mapped[str] = mapped_column(String(100))
    width: Mapped[int] = mapped_column()
    height: Mapped[int] = mapped_column()

    publisher: Mapped["Publisher"] = relationship(back_populates="ad_units")
