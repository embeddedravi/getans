from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

_PK = BigInteger().with_variant(Integer, "sqlite")


class TicketStatus(str, PyEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, PyEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TicketCategory(str, PyEnum):
    ACCOUNT = "account"
    BILLING = "billing"
    CAMPAIGN = "campaign"
    CREATIVE = "creative"
    AD_DELIVERY = "ad_delivery"
    PAYOUT = "payout"
    OTHER = "other"


class SupportTicket(TimestampMixin, Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[TicketCategory] = mapped_column(Enum(TicketCategory, native_enum=False), default=TicketCategory.OTHER, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(Enum(TicketStatus, native_enum=False), default=TicketStatus.OPEN, nullable=False, index=True)
    priority: Mapped[TicketPriority] = mapped_column(Enum(TicketPriority, native_enum=False), default=TicketPriority.NORMAL, nullable=False, index=True)

    messages: Mapped[List["SupportTicketMessage"]] = relationship(back_populates="ticket", cascade="all, delete-orphan", order_by="SupportTicketMessage.created_at")

    __table_args__ = (Index("ix_support_tickets_updated", "updated_at"),)


class SupportTicketMessage(Base):
    __tablename__ = "support_ticket_messages"

    id: Mapped[int] = mapped_column(_PK, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")
