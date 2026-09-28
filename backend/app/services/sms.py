"""SMS delivery. Swap the body of `send_sms` for your provider (MSG91, Twilio, etc.)."""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def send_sms(mobile: str, message: str) -> None:
    if settings.sms_backend == "console":
        # DEV ONLY: prints the message (including the OTP) to the server log.
        logger.warning("SMS to %s: %s", mobile, message)
        return
    raise NotImplementedError(
        f"SMS backend {settings.sms_backend!r} is not implemented; edit app/services/sms.py"
    )
