from __future__ import annotations

from pydantic import BaseModel


class PublisherCreate(BaseModel):
    name: str
    site_url: str


class PublisherOut(BaseModel):
    id: int
    name: str
    site_url: str
    api_key: str
    is_active: bool

    model_config = {"from_attributes": True}


class AdUnitCreate(BaseModel):
    publisher_id: int
    slot_name: str
    width: int
    height: int


class AdUnitOut(BaseModel):
    id: int
    publisher_id: int
    slot_name: str
    width: int
    height: int

    model_config = {"from_attributes": True}
