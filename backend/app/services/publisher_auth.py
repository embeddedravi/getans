"""API-key authentication service for publisher-facing integration endpoints and websockets."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.publisher import Publisher, PublisherStatus


async def authenticate_publisher(api_key: str) -> Optional[Publisher]:
    """Authenticates a publisher via API key and checks account status."""
    if not api_key:
        return None

    async with async_session_factory() as db:
        result = await db.execute(
            select(Publisher).where(
                Publisher.api_key == api_key,
                Publisher.is_active.is_(True),
                Publisher.status == PublisherStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()