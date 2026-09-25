from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TargetingRules(BaseModel):
    countries: list[str] | None = None
    device_types: list[str] | None = None
    keywords: list[str] | None = None


class CampaignCreate(BaseModel):
    advertiser_id: int
    name: str
    priority: int = 1
    daily_cap: float | None = Field(default=None, ge=0)
    start_date: datetime
    end_date: datetime
    targeting_rules: TargetingRules | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    priority: int | None = None
    daily_cap: float | None = Field(default=None, ge=0)
    start_date: datetime | None = None
    end_date: datetime | None = None
    targeting_rules: TargetingRules | None = None


class CampaignOut(BaseModel):
    id: int
    advertiser_id: int
    name: str
    is_active: bool
    priority: int
    daily_cap: float | None
    start_date: datetime
    end_date: datetime
    targeting_rules: dict | None

    model_config = {"from_attributes": True}
