from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_role
from app.models.payment import Payout, PayoutStatus
from app.models.publisher import PaymentMethod, Publisher
from app.models.user import User
from app.schemas.payment import PayoutCreate, PayoutOut, PayoutUpdate

router = APIRouter(tags=["Payouts"])

_OPEN = (PayoutStatus.PENDING, PayoutStatus.PROCESSING)
_ALLOWED = {
    PayoutStatus.PENDING: {
        PayoutStatus.PROCESSING, PayoutStatus.PAID, PayoutStatus.FAILED, PayoutStatus.CANCELLED,
    },
    PayoutStatus.PROCESSING: {PayoutStatus.PAID, PayoutStatus.FAILED, PayoutStatus.CANCELLED},
}


async def _lock_publisher(db: AsyncSession, publisher_id: int) -> Publisher:
    # FOR UPDATE serialises concurrent payouts on MySQL; SQLite ignores it.
    publisher = (
        await db.execute(select(Publisher).where(Publisher.id == publisher_id).with_for_update())
    ).scalar_one_or_none()
    if publisher is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Publisher not found")
    return publisher


async def _reserved(db: AsyncSession, publisher_id: int) -> Decimal:
    total = await db.scalar(
        select(func.coalesce(func.sum(Payout.amount), 0)).where(
            Payout.publisher_id == publisher_id, Payout.status.in_(_OPEN)
        )
    )
    return Decimal(total or 0)


def _check_access(user: User, publisher_id: int) -> None:
    if user.role == "publisher" and user.publisher_id != publisher_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied to requested payout")


@router.post("", response_model=PayoutOut, status_code=status.HTTP_201_CREATED,
             summary="Create a payout for a publisher (admin only)")
async def create_payout(
    payload: PayoutCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> Payout:
    if payload.period_start and payload.period_end and payload.period_end < payload.period_start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "period_end must not be before period_start")

    publisher = await _lock_publisher(db, payload.publisher_id)
    available = publisher.unpaid_earnings - await _reserved(db, publisher.id)
    if payload.amount > available:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Amount exceeds available unpaid earnings ({available:.2f})",
        )

    payout = Payout(
        publisher_id=publisher.id,
        amount=payload.amount,
        payment_method=PaymentMethod(payload.payment_method.value) if payload.payment_method
        else publisher.payment_method,
        payout_email=publisher.payout_email,  # snapshot
        period_start=payload.period_start,
        period_end=payload.period_end,
        notes=payload.notes,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)
    return payout


@router.get("", response_model=List[PayoutOut], summary="List payouts")
async def list_payouts(
    publisher_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> List[Payout]:
    stmt = select(Payout).order_by(Payout.id.desc()).offset(skip).limit(limit)
    if user.role == "publisher":
        stmt = stmt.where(Payout.publisher_id == user.publisher_id)
    elif publisher_id is not None:
        stmt = stmt.where(Payout.publisher_id == publisher_id)
    if status_filter:
        try:
            stmt = stmt.where(Payout.status == PayoutStatus(status_filter))
        except ValueError:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown payout status")
    return list((await db.execute(stmt)).scalars().all())


@router.get("/{payout_id}", response_model=PayoutOut, summary="Get a payout")
async def get_payout(
    payout_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "publisher")),
) -> Payout:
    payout = await db.get(Payout, payout_id)
    if payout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout not found")
    _check_access(user, payout.publisher_id)
    return payout


@router.patch("/{payout_id}", response_model=PayoutOut,
              summary="Update payout status/reference (admin only)")
async def update_payout(
    payout_id: int,
    payload: PayoutUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
) -> Payout:
    payout = await db.get(Payout, payout_id)
    if payout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payout not found")
    if payout.status not in _OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Payout is already {payout.status.value}")

    publisher = await _lock_publisher(db, payout.publisher_id)
    updates = payload.model_dump(exclude_unset=True)

    new_status = PayoutStatus(payload.status.value) if payload.status else None
    if new_status and new_status != payout.status:
        if new_status not in _ALLOWED[payout.status]:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Cannot move payout from {payout.status.value} to {new_status.value}",
            )
        if new_status == PayoutStatus.FAILED and not (
            payload.failure_reason or payout.failure_reason
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "failure_reason is required when failing a payout")
        if new_status == PayoutStatus.PAID:
            if publisher.unpaid_earnings < payout.amount:
                raise HTTPException(status.HTTP_409_CONFLICT, "Publisher's unpaid earnings are lower than this payout")
            publisher.unpaid_earnings -= payout.amount
            payout.paid_at = datetime.now(timezone.utc)
        payout.status = new_status

    for field in ("reference", "failure_reason", "notes"):
        if field in updates:
            setattr(payout, field, updates[field])

    await db.commit()
    await db.refresh(payout)
    return payout