from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.phone import normalize_indian_mobile


class OTPRequest(BaseModel):
    mobile: str = Field(..., description="Indian mobile number")

    @field_validator("mobile")
    @classmethod
    def _normalize_mobile(cls, v: str) -> str:
        return normalize_indian_mobile(v)


class OTPVerify(OTPRequest):
    code: str = Field(..., pattern=r"^\d{6}$", description="6-digit code sent by SMS")


class OTPRequestResponse(BaseModel):
    message: str
    expires_in: int
    resend_after: int
