from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.publisher import PaymentMethod  # reuse the existing enum

if TYPE_CHECKING:
    from app.models.publisher import Publisher

# BigInteger PKs don't autoincrement on SQLite (used by the test suite).
_PK = BigInteger().with_variant(Integer, "sqlite")


class PayoutStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Payout(TimestampMixin, Base):
    """A payment made (or being made) to a publisher out of their unpaid earnings."""

    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)

    publisher_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(precision=12, scale=2), nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(
        Enum(PayoutStatus, native_enum=False),
        default=PayoutStatus.PENDING,
        nullable=False,
        index=True,
    )
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(
        Enum(PaymentMethod, native_enum=False), nullable=True
    )
    payout_email: Mapped[str] = mapped_column(String(255), nullable=False)  # snapshot at payout time
    reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, unique=True)  # gateway txn id
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    publisher: Mapped["Publisher"] = relationship("Publisher", back_populates="payouts", lazy="joined")

    __table_args__ = (
        CheckConstraint("amount > 0.00", name="check_positive_payout_amount"),
        CheckConstraint(
            "period_end IS NULL OR period_start IS NULL OR period_end >= period_start",
            name="check_valid_payout_period",
        ),
        Index("ix_payouts_publisher_status", "publisher_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Payout(id={self.id}, publisher_id={self.publisher_id}, amount={self.amount}, status='{self.status.value}')>"