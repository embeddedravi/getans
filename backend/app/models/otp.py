from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

# BigInteger PKs don't autoincrement on SQLite (used by the test suite).
_PK = BigInteger().with_variant(Integer, "sqlite")


class OTPCode(TimestampMixin, Base):
    """A one-time code issued to a mobile number. Only an HMAC of the code is stored."""

    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    mobile: Mapped[str] = mapped_column(String(15), nullable=False, index=True)  # +91XXXXXXXXXX
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
