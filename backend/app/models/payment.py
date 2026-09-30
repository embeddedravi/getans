from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ad_unit import AdUnit
    from app.models.campaign import Campaign
    from app.models.creative import Creative


    
    

    