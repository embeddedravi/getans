"""SMS delivery using the development console or Twilio's Messages API."""

from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def send_sms(mobile: str, message: str) -> None:
    if settings.sms_backend == "console":
        # DEV ONLY: prints the message (including the OTP) to the server log.
        logger.warning("SMS to %s: %s", mobile, message)
        return
    if settings.sms_backend == "twilio":
        sid = settings.twilio_account_sid
        token = settings.twilio_auth_token
        sender = settings.twilio_from_number
        if not sid or not token or not sender:
            raise RuntimeError("Twilio SMS configuration is incomplete")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{quote(sid, safe='')}/Messages.json"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                url,
                auth=(sid, token.get_secret_value()),
                data={"To": mobile, "From": sender, "Body": message},
            )
            response.raise_for_status()
        return
    raise NotImplementedError(
        f"SMS backend {settings.sms_backend!r} is not implemented; edit app/services/sms.py"
    )
