from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MediaKind(str, Enum):
    IMAGE = "image"
    VIDEO = "video"


class MediaAssetOut(BaseModel):
    id: int
    advertiser_id: int
    kind: MediaKind
    original_filename: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    duration_seconds: Optional[Decimal] = None
    url: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)