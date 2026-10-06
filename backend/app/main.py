"""
App entrypoint. Mounts a Socket.IO ASGI app on top of FastAPI so REST
endpoints (dashboard-facing) and Socket.IO namespaces (ad delivery +
dashboard live metrics) share one process.

Run with:
    uvicorn app.main:asgi_app --reload
"""

from __future__ import annotations

import logging

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.sockets.dashboard_ns import register_dashboard_namespace
from app.sockets.delivery_ns import register_delivery_namespace

logging.basicConfig(level=logging.INFO)

fastapi_app = FastAPI(title="Ad Platform API")

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import analytics, auth, campaigns, creatives, payouts, publishers, otp, admin  # noqa: E402

fastapi_app.include_router(auth.router, prefix="/api", tags=["auth"])
fastapi_app.include_router(publishers.router, prefix="/api", tags=["publishers"])
fastapi_app.include_router(campaigns.router, prefix="/api", tags=["campaigns"])
fastapi_app.include_router(creatives.router, prefix="/api", tags=["creatives"])
fastapi_app.include_router(otp.router, prefix="/api/auth/otp", tags=["otp"])
fastapi_app.include_router(analytics.router, prefix="/api", tags=["analytics"])
fastapi_app.include_router(payouts.router, prefix="/api/payouts", tags=["payouts"])
fastapi_app.include_router(admin.router, prefix="/api", tags=["admin"])

@fastapi_app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


sio = socketio.AsyncServer(
    async_mode=settings.socketio_async_mode,
    cors_allowed_origins=settings.socketio_cors_allowed_origins,
)

register_delivery_namespace(sio)
register_dashboard_namespace(sio)

asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)