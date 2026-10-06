from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AdReport(Base):
    """A visitor report for a creative shown in an ad unit."""

    __tablename__ = "ad_reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ad_unit_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("ad_units.id", ondelete="CASCADE"), nullable=False, index=True
    )
    creative_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("creatives.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reporter_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    review_round: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reason: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "ad_unit_id", "review_round", "reporter_hash", name="uq_ad_reports_visitor_round"
        ),
    )
