from __future__ import annotations

from pydantic import BaseModel


class CreativeCreate(BaseModel):
    campaign_id: int
    asset_url: str
    click_url: str
    format: str = "image"
    width: int
    height: int


class CreativeOut(BaseModel):
    id: int
    campaign_id: int
    asset_url: str
    click_url: str
    format: str
    width: int
    height: int

    model_config = {"from_attributes": True}
