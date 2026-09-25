"""Shared async Redis client, used for budget counters and dashboard pub/sub."""

from __future__ import annotations

import redis.asyncio as redis

from app.config import settings

redis_client: redis.Redis = redis.from_url(
    settings.redis_url,
    decode_responses=True,
)

DASHBOARD_METRICS_CHANNEL = "dashboard:metrics"
