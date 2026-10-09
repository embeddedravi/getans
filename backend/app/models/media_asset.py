from __future__ import annotations

from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.config import settings
from app.db.base import Base, TimestampMixin

_PK = BigInteger().with_variant(Integer, "sqlite")


class MediaKind(str, PyEnum):
    IMAGE = "image"
    VIDEO = "video"


class MediaAsset(TimestampMixin, Base):
    """An uploaded image/video owned by one advertiser."""

    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    advertiser_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("advertisers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[MediaKind] = mapped_column(Enum(MediaKind, native_enum=False), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)

    @property
    def url(self) -> str:
        return f"{settings.public_base_url.rstrip('/')}/uploads/{self.stored_name}"