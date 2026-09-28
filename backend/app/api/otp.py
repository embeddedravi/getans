"""Mobile-number verification via SMS OTP.

Include in main.py *without* an internal prefix, e.g.:
    fastapi_app.include_router(otp.router, prefix="/api/auth/otp", tags=["otp"])
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.models.user import User
from app.schemas.otp import OTPRequest, OTPRequestResponse, OTPVerify
from app.schemas.user import MessageResponse
from app.services.otp import OTPRateLimitError, issue_otp, verify_otp
from app.services.sms import send_sms

router = APIRouter()


async def _get_user(db: AsyncSession, mobile: str) -> User | None:
    return (await db.execute(select(User).where(User.mobile == mobile))).scalar_one_or_none()


@router.post(
    "/request",
    response_model=OTPRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a verification code to a registered mobile number",
)
async def request_otp(payload: OTPRequest, db: AsyncSession = Depends(get_db)) -> OTPRequestResponse:
    user = await _get_user(db, payload.mobile)
    # Same response whether or not the number is registered, so this can't be used
    # to discover which numbers have accounts.
    if user is not None and user.is_active:
        try:
            code = await issue_otp(db, payload.mobile)
        except OTPRateLimitError as exc:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                str(exc),
                headers={"Retry-After": str(exc.retry_after)},
            )
        minutes = max(1, settings.otp_ttl_seconds // 60)
        await send_sms(
            payload.mobile,
            f"{code} is your Ad Platform verification code. It expires in {minutes} minutes.",
        )
    return OTPRequestResponse(
        message="If this number is registered, a code has been sent",
        expires_in=settings.otp_ttl_seconds,
        resend_after=settings.otp_resend_cooldown_seconds,
    )


@router.post(
    "/verify",
    response_model=MessageResponse,
    summary="Verify a mobile number with the code received by SMS",
)
async def verify(payload: OTPVerify, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired code")

    user = await _get_user(db, payload.mobile)
    if user is None or not await verify_otp(db, payload.mobile, payload.code):
        raise invalid

    user.is_verified = True
    await db.commit()
    return MessageResponse(message="Mobile number verified")
