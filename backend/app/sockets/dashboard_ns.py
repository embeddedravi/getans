"""
Socket.IO namespace pushing live metrics to dashboard clients.

Authentication: clients must connect with a dashboard JWT in the Socket.IO
`auth` payload -- `io("/dashboard", { auth: { token } })`. The user is
re-loaded from the database (roles in the token are not trusted) and placed
in a room scoped to their account:

    admin       -> "admin"                 (sees every event)
    advertiser  -> "advertiser:{id}"       (events for their campaigns)
    publisher   -> "publisher:{id}"        (events for their ad units)

Connections are closed when the token expires.

Events:
    server -> client: "metric_update"  { type, campaign_id, ad_unit_id, timestamp }
"""

from __future__ import annotations

import asyncio
import logging
import time

import jwt
import socketio
from socketio.exceptions import ConnectionRefusedError

from app.config import settings
from app.core.security import decode_access_token
from app.db.session import async_session_factory
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

_sio: socketio.AsyncServer | None = None

ADMIN_ROOM = "admin"


def advertiser_room(advertiser_id: int) -> str:
    return f"advertiser:{advertiser_id}"


def publisher_room(publisher_id: int) -> str:
    return f"publisher:{publisher_id}"


def _rooms_for(user: User) -> list[str]:
    if user.role == UserRole.ADMIN:
        return [ADMIN_ROOM]
    if user.role == UserRole.ADVERTISER and user.advertiser_id is not None:
        return [advertiser_room(user.advertiser_id)]
    if user.role == UserRole.PUBLISHER and user.publisher_id is not None:
        return [publisher_room(user.publisher_id)]
    return []


async def _load_user(user_id: int) -> User | None:
    async with async_session_factory() as db:
        return await db.get(User, user_id)


async def _authenticate(auth: object) -> tuple[User, dict]:
    """Validate the handshake `auth` payload. Every failure raises the same
    generic error so clients can't probe why a token was rejected."""
    refused = ConnectionRefusedError("unauthorized")

    token = auth.get("token") if isinstance(auth, dict) else None
    if not token or not isinstance(token, str):
        raise refused

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise refused from None

    user = await _load_user(user_id)
    if user is None or not user.is_active:
        raise refused
    if settings.require_verified_mobile and not user.is_verified:
        raise refused

    return user, payload


class DashboardNamespace(socketio.AsyncNamespace):
    def __init__(self, namespace: str = "/dashboard") -> None:
        super().__init__(namespace)
        self._expiry_tasks: dict[str, asyncio.Task] = {}

    async def on_connect(self, sid: str, environ: dict, auth: object = None) -> None:
        user, payload = await _authenticate(auth)

        rooms = _rooms_for(user)
        if not rooms:
            raise ConnectionRefusedError("unauthorized")
        for room in rooms:
            await self.enter_room(sid, room)

        exp = payload.get("exp")
        if exp is not None:
            self._expiry_tasks[sid] = asyncio.create_task(
                self._disconnect_at_expiry(sid, float(exp) - time.time())
            )

        logger.debug("Dashboard client connected: %s (user=%s, rooms=%s)", sid, user.id, rooms)

    async def on_disconnect(self, sid: str, *args: object) -> None:
        task = self._expiry_tasks.pop(sid, None)
        if task is not None:
            task.cancel()
        logger.debug("Dashboard client disconnected: %s", sid)

    async def _disconnect_at_expiry(self, sid: str, delay: float) -> None:
        await asyncio.sleep(max(0.0, delay))
        self._expiry_tasks.pop(sid, None)  # so on_disconnect doesn't cancel us mid-flight
        logger.info("Dashboard token expired; disconnecting %s", sid)
        await self.disconnect(sid)


async def emit_metric_update(
    payload: dict,
    *,
    advertiser_id: int | None = None,
    publisher_id: int | None = None,
) -> None:
    """Send a metric to the admin room plus the owning advertiser/publisher rooms.
    Never broadcasts to the whole namespace."""
    if _sio is None:
        logger.warning("Dashboard namespace not registered; dropping metric_update")
        return

    rooms = [ADMIN_ROOM]
    if advertiser_id is not None:
        rooms.append(advertiser_room(advertiser_id))
    if publisher_id is not None:
        rooms.append(publisher_room(publisher_id))

    for room in rooms:
        await _sio.emit("metric_update", payload, room=room, namespace="/dashboard")


def register_dashboard_namespace(sio: socketio.AsyncServer) -> None:
    global _sio
    _sio = sio
    sio.register_namespace(DashboardNamespace("/dashboard"))