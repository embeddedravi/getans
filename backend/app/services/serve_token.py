"""Signed, short lived proof that a specific ad was served to a visitor."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from app.config import settings

TOKEN_TTL_SECONDS = 300


def issue_serve_token(ad_unit_id: int, creative_id: int, visitor_id: str | None = None) -> tuple[str, str]:
    visitor = visitor_id or secrets.token_urlsafe(24)
    payload = {"u": int(ad_unit_id), "c": int(creative_id), "v": visitor, "e": int(time.time()) + TOKEN_TTL_SECONDS}
    body = urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).rstrip(b"=")
    key = settings.jwt_secret.get_secret_value().encode()
    sig = hmac.new(key, body, hashlib.sha256).digest()
    return body.decode() + "." + urlsafe_b64encode(sig).rstrip(b"=").decode(), visitor


def verify_serve_token(token: str, ad_unit_id: int, creative_id: int) -> str | None:
    try:
        body_text, sig_text = token.split(".", 1)
        body = body_text.encode()
        decode = lambda value: urlsafe_b64decode(value + "=" * (-len(value) % 4))
        key = settings.jwt_secret.get_secret_value().encode()
        if not hmac.compare_digest(hmac.new(key, body, hashlib.sha256).digest(), decode(sig_text)):
            return None
        payload = json.loads(decode(body_text))
        if payload["e"] < int(time.time()) or payload["u"] != int(ad_unit_id) or payload["c"] != int(creative_id):
            return None
        return payload["v"]
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
