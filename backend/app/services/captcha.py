"""Small first-party arithmetic CAPTCHA with signed, expiring challenges."""

import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, status

from app.config import settings


def _key() -> bytes:
    return hmac.new(settings.jwt_secret.get_secret_value().encode(), b"getans:captcha:v1", hashlib.sha256).digest()


def issue_captcha() -> dict[str, str]:
    left, right = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
    expires = int(time.time()) + 300
    nonce = secrets.token_urlsafe(12)
    body = f"{left}.{right}.{expires}.{nonce}"
    signature = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
    return {"challenge": f"{body}.{signature}", "question": f"What is {left} + {right}?"}


async def verify_captcha(challenge: str | None, answer: str | None) -> None:
    invalid = HTTPException(status.HTTP_400_BAD_REQUEST, "CAPTCHA answer is incorrect or expired. Please try again.")
    if not challenge or not answer or len(challenge) > 256 or len(answer) > 3:
        raise invalid
    try:
        left, right, expires, nonce, signature = challenge.split(".")
        body = f"{left}.{right}.{expires}.{nonce}"
        expected = hmac.new(_key(), body.encode(), hashlib.sha256).hexdigest()
        valid = (
            left.isdigit() and right.isdigit() and expires.isdigit()
            and int(expires) >= int(time.time()) and int(expires) <= int(time.time()) + 300
            and hmac.compare_digest(signature, expected)
            and int(answer) == int(left) + int(right)
        )
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise invalid
