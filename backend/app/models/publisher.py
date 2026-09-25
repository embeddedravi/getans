from __future__ import annotations

import secrets

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


def _generate_api_key() -> str:
    return secrets.token_urlsafe(32)


class Publisher(TimestampMixin, Base):
    __tablename__ = "publishers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    site_url: Mapped[str] = mapped_column(String(500))
    api_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, default=_generate_api_key
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    ad_units: Mapped[list["AdUnit"]] = relationship(back_populates="publisher")
