"""OTP issuing and verification with expiry, resend cooldown, hourly cap and attempt limits."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.otp import OTPCode


class OTPRateLimitError(Exception):
    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; treat them as UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _hash(mobile: str, code: str) -> str:
    key = settings.jwt_secret.get_secret_value().encode()
    return hmac.new(key, f"{mobile}:{code}".encode(), hashlib.sha256).hexdigest()


async def issue_otp(db: AsyncSession, mobile: str) -> str:
    """Create a new code for `mobile`, invalidating any previous unused ones. Returns the plaintext code."""
    now = _now()

    last_created = (
        await db.execute(select(func.max(OTPCode.created_at)).where(OTPCode.mobile == mobile))
    ).scalar_one_or_none()
    if last_created is not None:
        wait = settings.otp_resend_cooldown_seconds - (now - _aware(last_created)).total_seconds()
        if wait > 0:
            raise OTPRateLimitError("Please wait before requesting another code", int(wait) + 1)

    sent_last_hour = (
        await db.execute(
            select(func.count())
            .select_from(OTPCode)
            .where(OTPCode.mobile == mobile, OTPCode.created_at >= now - timedelta(hours=1))
        )
    ).scalar_one()
    if sent_last_hour >= settings.otp_max_per_hour:
        raise OTPRateLimitError("Too many codes requested. Try again later", 3600)

    await db.execute(
        update(OTPCode)
        .where(OTPCode.mobile == mobile, OTPCode.consumed_at.is_(None))
        .values(consumed_at=now)
    )

    code = f"{secrets.randbelow(10 ** settings.otp_length):0{settings.otp_length}d}"
    db.add(
        OTPCode(
            mobile=mobile,
            code_hash=_hash(mobile, code),
            expires_at=now + timedelta(seconds=settings.otp_ttl_seconds),
        )
    )
    await db.commit()
    return code


async def verify_otp(db: AsyncSession, mobile: str, code: str) -> bool:
    """True only if `code` matches the latest live code for `mobile`. Consumes it on success."""
    now = _now()
    otp = (
        await db.execute(
            select(OTPCode)
            .where(OTPCode.mobile == mobile, OTPCode.consumed_at.is_(None))
            .order_by(OTPCode.created_at.desc(), OTPCode.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if otp is None or _aware(otp.expires_at) <= now or otp.attempts >= settings.otp_max_attempts:
        return False

    otp.attempts += 1
    if hmac.compare_digest(otp.code_hash, _hash(mobile, code)):
        otp.consumed_at = now
        await db.commit()
        return True

    await db.commit()  # persist the failed attempt
    return False
