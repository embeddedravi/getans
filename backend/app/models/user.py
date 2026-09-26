from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.advertiser import Advertiser
    from app.models.publisher import Publisher


class UserRole(str, PyEnum):
    ADMIN = "admin"
    PUBLISHER = "publisher"
    ADVERTISER = "advertiser"


class User(TimestampMixin, Base):
    """A dashboard login -- either a publisher-side, advertiser-side, or platform admin user."""

    __tablename__ = "users"

    # Primary Key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Core Identity & Authentication
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Role & Permissions
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        nullable=False,
        index=True,
    )
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Multi-Tenant FK Mappings
    publisher_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("publishers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    advertiser_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("advertisers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Account State & Security
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Audit & Tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # Fits IPv6

    # Relationships
    publisher: Mapped[Optional["Publisher"]] = relationship(
        "Publisher",
        back_populates="users",
        lazy="joined",
    )
    advertiser: Mapped[Optional["Advertiser"]] = relationship(
        "Advertiser",
        back_populates="users",
        lazy="joined",
    )

    # Constraints & Indexes
    __table_args__ = (
        # Ensures publisher users only tie to publishers, advertiser users to advertisers, etc.
        CheckConstraint(
            """
            (role = 'admin') OR
            (role = 'publisher' AND publisher_id IS NOT NULL AND advertiser_id IS NULL) OR
            (role = 'advertiser' AND advertiser_id IS NOT NULL AND publisher_id IS NULL)
            """,
            name="check_user_role_tenant_integrity",
        ),
        Index("ix_users_role_active", "role", "is_active"),
    )

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"