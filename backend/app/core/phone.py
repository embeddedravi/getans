"""Indian mobile number validation and normalization."""

from __future__ import annotations

import re

_SEPARATORS = re.compile(r"[\s\-()]")
_TEN_DIGITS = re.compile(r"[6-9]\d{9}")  # Indian mobiles start with 6-9


def normalize_indian_mobile(value: str) -> str:
    """Return the number as +91XXXXXXXXXX or raise ValueError."""
    num = _SEPARATORS.sub("", value.strip())

    if num.startswith("+91"):
        num = num[3:]
    elif num.startswith("91") and len(num) == 12:
        num = num[2:]
    elif num.startswith("0") and len(num) == 11:
        num = num[1:]

    if not _TEN_DIGITS.fullmatch(num):
        raise ValueError("Enter a valid 10-digit Indian mobile number")
    return f"+91{num}"