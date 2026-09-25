from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Advertiser(TimestampMixin, Base):
    __tablename__ = "advertisers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    billing_email: Mapped[str] = mapped_column(String(255))

    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="advertiser")
