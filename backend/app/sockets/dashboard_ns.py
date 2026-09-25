"""
Socket.IO namespace pushing live metrics to dashboard clients.

Dashboard clients don't talk to the ad-serving pipeline directly -- they
subscribe here, and this namespace relays messages published by
budget_tracker.record_event() over Redis pub/sub. This keeps ad-serving
throughput independent of how many dashboards happen to be open.

Events:
    server -> client: "metric_update"  { type, campaign_id, ad_unit_id, timestamp }
"""

from __future__ import annotations

import asyncio
import json
import logging

import socketio

from app.core.redis_client import DASHBOARD_METRICS_CHANNEL, redis_client

logger = logging.getLogger(__name__)


class DashboardNamespace(socketio.AsyncNamespace):
    async def on_connect(self, sid: str, environ: dict) -> None:
        # TODO: authenticate the dashboard user (JWT in query string / auth header)
        # and join a room scoped to their publisher/advertiser account so they
        # only see their own metrics.
        logger.debug("Dashboard client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.debug("Dashboard client disconnected: %s", sid)


async def start_dashboard_relay(sio: socketio.AsyncServer) -> None:
    """Background task: subscribes to Redis and relays messages to Socket.IO clients.

    Call this once at app startup, e.g.:
        asyncio.create_task(start_dashboard_relay(sio))
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(DASHBOARD_METRICS_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except (TypeError, json.JSONDecodeError):
                logger.warning("Bad dashboard metrics payload: %r", message["data"])
                continue

            await sio.emit("metric_update", payload, namespace="/dashboard")
    except asyncio.CancelledError:
        await pubsub.unsubscribe(DASHBOARD_METRICS_CHANNEL)
        raise


def register_dashboard_namespace(sio: socketio.AsyncServer) -> None:
    sio.register_namespace(DashboardNamespace("/dashboard"))
