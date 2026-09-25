"""API-key auth for publisher-facing Socket.IO connections.

This is deliberately simple (a DB lookup by api_key, cached in Redis for
speed since it runs on every ad request). Rotate keys via the dashboard API,
not by editing the DB directly, so old keys can be invalidated.
"""

from __future__ import annotations

from sqlalchemy import select

from app.core.redis_client import redis_client
from app.db.session import async_session_factory
from app.models.publisher import Publisher

_CACHE_TTL_SECONDS = 60


async def authenticate_publisher(api_key: str) -> Publisher | None:
    cache_key = f"publisher_auth:{api_key}"

    cached_id = await redis_client.get(cache_key)
    if cached_id == "invalid":
        return None

    async with async_session_factory() as db:
        if cached_id is not None:
            publisher = await db.get(Publisher, int(cached_id))
        else:
            result = await db.execute(
                select(Publisher).where(
                    Publisher.api_key == api_key, Publisher.is_active.is_(True)
                )
            )
            publisher = result.scalar_one_or_none()

    if publisher is None:
        await redis_client.set(cache_key, "invalid", ex=_CACHE_TTL_SECONDS)
        return None

    await redis_client.set(cache_key, str(publisher.id), ex=_CACHE_TTL_SECONDS)
    return publisher
