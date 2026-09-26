"""API-key auth for publisher-facing Socket.IO connections.

Simplified: no Redis caching layer. Each ad request does a direct DB lookup.
Fine for low/moderate traffic; if this becomes a bottleneck, reintroduce a
cache (Redis or an in-memory TTL cache) in front of this function.
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.publisher import Publisher


async def authenticate_publisher(api_key: str) -> Publisher | None:
    async with async_session_factory() as db:
        result = await db.execute(
            select(Publisher).where(
                Publisher.api_key == api_key, Publisher.is_active.is_(True)
            )
        )
        return result.scalar_one_or_none()