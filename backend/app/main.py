"""
App entrypoint. Mounts a Socket.IO ASGI app on top of FastAPI so REST
endpoints (dashboard-facing) and Socket.IO namespaces (ad delivery +
dashboard live metrics) share one process.

Run with:
    uvicorn app.main:asgi_app --reload
"""

from __future__ import annotations

import asyncio
import logging

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.sockets.dashboard_ns import register_dashboard_namespace, start_dashboard_relay
from app.sockets.delivery_ns import register_delivery_namespace

logging.basicConfig(level=logging.INFO)

# --- FastAPI app (REST API for the dashboard) -------------------------------

fastapi_app = FastAPI(title="Ad Platform API")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import analytics, auth, campaigns, creatives, publishers  # noqa: E402

fastapi_app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
fastapi_app.include_router(publishers.router, prefix="/api/publishers", tags=["publishers"])
fastapi_app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])
fastapi_app.include_router(creatives.router, prefix="/api/creatives", tags=["creatives"])
fastapi_app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])


@fastapi_app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# --- Socket.IO server ---------------------------------------------------------

sio = socketio.AsyncServer(
    async_mode=settings.socketio_async_mode,
    cors_allowed_origins=settings.socketio_cors_allowed_origins,
)

register_delivery_namespace(sio)
register_dashboard_namespace(sio)


@fastapi_app.on_event("startup")
async def start_background_tasks() -> None:
    asyncio.create_task(start_dashboard_relay(sio))


# Combined ASGI app: Socket.IO handles /socket.io/*, everything else goes to FastAPI.
asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
