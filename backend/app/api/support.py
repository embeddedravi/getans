"""Customer support ticket and staff queue endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.support_ticket import (
    SupportTicket,
    SupportTicketMessage,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)
from app.models.user import User, UserRole

router = APIRouter(prefix="/support", tags=["Customer Support"])
CUSTOMER_ROLES = (UserRole.ADVERTISER, UserRole.PUBLISHER)
STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN)


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    category: TicketCategory = TicketCategory.OTHER
    message: str = Field(min_length=1, max_length=5000)

    @field_validator("subject", "message")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    is_internal: bool = False

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class TicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    assigned_to_id: int | None = None

    @model_validator(mode="after")
    def reject_null_workflow_fields(self):
        for field in ("status", "priority"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


def _summary(ticket: SupportTicket, customer: User) -> dict:
    return {
        "id": ticket.id,
        "subject": ticket.subject,
        "category": ticket.category.value,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "user_id": ticket.user_id,
        "customer_name": customer.full_name,
        "customer_email": customer.email,
        "customer_mobile": customer.mobile,
        "assigned_to_id": ticket.assigned_to_id,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


async def _get_accessible_ticket(db: AsyncSession, ticket_id: int, user: User) -> SupportTicket:
    ticket = await db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Support ticket not found")
    if user.role in CUSTOMER_ROLES and ticket.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Support ticket not found")
    if user.role not in CUSTOMER_ROLES + STAFF_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")
    return ticket


@router.get("/tickets")
async def list_tickets(
    ticket_status: TicketStatus | None = Query(None, alias="status"),
    priority: TicketPriority | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser", "publisher", "staff", "admin")),
) -> list[dict]:
    stmt = select(SupportTicket, User).join(User, User.id == SupportTicket.user_id)
    if user.role in CUSTOMER_ROLES:
        stmt = stmt.where(SupportTicket.user_id == user.id)
    if ticket_status is not None:
        stmt = stmt.where(SupportTicket.status == ticket_status)
    if priority is not None:
        stmt = stmt.where(SupportTicket.priority == priority)
    rows = (await db.execute(stmt.order_by(SupportTicket.updated_at.desc()))).all()
    return [_summary(ticket, customer) for ticket, customer in rows]


@router.get("/staff")
async def list_support_staff(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("staff", "admin")),
) -> list[dict]:
    users = (await db.execute(
        select(User).where(User.role.in_(STAFF_ROLES), User.is_active.is_(True)).order_by(User.role, User.first_name, User.last_name)
    )).scalars().all()
    return [{"id": person.id, "name": person.full_name, "role": person.role.value} for person in users]


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser", "publisher")),
) -> dict:
    ticket = SupportTicket(user_id=user.id, subject=payload.subject, category=payload.category)
    ticket.messages.append(SupportTicketMessage(author_id=user.id, body=payload.message))
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return _summary(ticket, user)


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser", "publisher", "staff", "admin")),
) -> dict:
    ticket = await _get_accessible_ticket(db, ticket_id, user)
    customer = await db.get(User, ticket.user_id)
    message_stmt = (
        select(SupportTicketMessage, User)
        .join(User, User.id == SupportTicketMessage.author_id)
        .where(SupportTicketMessage.ticket_id == ticket.id)
    )
    if user.role not in STAFF_ROLES:
        message_stmt = message_stmt.where(SupportTicketMessage.is_internal.is_(False))
    messages = (await db.execute(message_stmt.order_by(SupportTicketMessage.created_at))).all()
    return {
        **_summary(ticket, customer),
        "messages": [
            {
                "id": message.id,
                "author_id": message.author_id,
                "author_name": author.full_name,
                "body": message.body,
                "is_internal": message.is_internal,
                "created_at": message.created_at.isoformat(),
            }
            for message, author in messages
        ],
    }


@router.post("/tickets/{ticket_id}/messages", status_code=status.HTTP_201_CREATED)
async def add_message(
    ticket_id: int,
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("advertiser", "publisher", "staff", "admin")),
) -> dict:
    ticket = await _get_accessible_ticket(db, ticket_id, user)
    is_staff = user.role in STAFF_ROLES
    if payload.is_internal and not is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only support staff can add internal notes")
    if ticket.status == TicketStatus.CLOSED and not is_staff:
        raise HTTPException(status.HTTP_409_CONFLICT, "This ticket is closed")
    message = SupportTicketMessage(
        ticket_id=ticket.id,
        author_id=user.id,
        body=payload.body,
        is_internal=payload.is_internal,
    )
    db.add(message)
    ticket.updated_at = datetime.now(timezone.utc)
    if not payload.is_internal:
        if is_staff and ticket.assigned_to_id is None:
            ticket.assigned_to_id = user.id
        if not is_staff and ticket.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
            ticket.status = TicketStatus.OPEN
        elif is_staff and ticket.status == TicketStatus.WAITING_ON_CUSTOMER:
            ticket.status = TicketStatus.IN_PROGRESS
    await db.commit()
    await db.refresh(message)
    return {
        "id": message.id,
        "author_id": user.id,
        "author_name": user.full_name,
        "body": message.body,
        "is_internal": message.is_internal,
        "created_at": message.created_at.isoformat(),
    }


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("staff", "admin")),
) -> dict:
    ticket = await db.get(SupportTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Support ticket not found")
    changes = payload.model_dump(exclude_unset=True)
    if "assigned_to_id" in changes and changes["assigned_to_id"] is not None:
        assignee = await db.get(User, changes["assigned_to_id"])
        if assignee is None or assignee.role not in STAFF_ROLES or not assignee.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assignee must be an active staff or admin user")
    for field, value in changes.items():
        setattr(ticket, field, value)
    await db.commit()
    customer = await db.get(User, ticket.user_id)
    return _summary(ticket, customer)
