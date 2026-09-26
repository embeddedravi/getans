"""
Socket.IO namespace pushing live metrics to dashboard clients.

No longer relayed through Redis pub/sub -- budget_tracker.record_event()
calls emit_metric_update() directly, since both run in the same process.

Events:
    server -> client: "metric_update"  { type, campaign_id, ad_unit_id, timestamp }
"""

from __future__ import annotations

import logging

import socketio

logger = logging.getLogger(__name__)

_sio: socketio.AsyncServer | None = None


class DashboardNamespace(socketio.AsyncNamespace):
    async def on_connect(self, sid: str, environ: dict) -> None:
        # TODO: authenticate the dashboard user (JWT in query string / auth header)
        # and join a room scoped to their publisher/advertiser account so they
        # only see their own metrics.
        logger.debug("Dashboard client connected: %s", sid)

    async def on_disconnect(self, sid: str) -> None:
        logger.debug("Dashboard client disconnected: %s", sid)


async def emit_metric_update(payload: dict) -> None:
    if _sio is None:
        logger.warning("Dashboard namespace not registered; dropping metric_update")
        return
    await _sio.emit("metric_update", payload, namespace="/dashboard")


def register_dashboard_namespace(sio: socketio.AsyncServer) -> None:
    global _sio
    _sio = sio
    sio.register_namespace(DashboardNamespace("/dashboard"))