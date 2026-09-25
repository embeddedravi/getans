"""Shared pytest fixtures.

Uses an in-memory SQLite DB (fast, no external services) and fakeredis in
place of the real Redis connection. Both are swapped in via monkeypatch on
each module's already-imported `redis_client` / session factory names,
since `from x import y` binds a local reference that patching the source
module alone won't affect.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.deps import get_db
from app.main import fastapi_app
from app.models.advertiser import Advertiser
from app.models.publisher import Publisher
from app.models.user import User

# --- Database -----------------------------------------------------------

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(autouse=True)
async def _create_schema():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with TestSessionFactory() as session:
        yield session


@pytest.fixture(autouse=True)
def _override_session_factory(monkeypatch):
    """Point every module that imported the real session factory at the test one."""
    monkeypatch.setattr("app.services.publisher_auth.async_session_factory", TestSessionFactory)
    monkeypatch.setattr("app.services.budget_tracker.async_session_factory", TestSessionFactory)


# --- Redis ---------------------------------------------------------------


@pytest_asyncio.fixture
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()


@pytest.fixture(autouse=True)
def _patch_redis(fake_redis, monkeypatch):
    monkeypatch.setattr("app.services.ad_selector.redis_client", fake_redis)
    monkeypatch.setattr("app.services.publisher_auth.redis_client", fake_redis)
    monkeypatch.setattr("app.services.budget_tracker.redis_client", fake_redis)


# --- HTTP client -----------------------------------------------------------


@pytest_asyncio.fixture
async def client(db):
    async def _get_db_override():
        yield db

    fastapi_app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


# --- Common test data ------------------------------------------------------


@pytest_asyncio.fixture
async def advertiser(db) -> Advertiser:
    adv = Advertiser(name="Acme Corp", billing_email="billing@acme.example")
    db.add(adv)
    await db.commit()
    await db.refresh(adv)
    return adv


@pytest_asyncio.fixture
async def publisher(db) -> Publisher:
    pub = Publisher(name="Example News", site_url="https://news.example.com")
    db.add(pub)
    await db.commit()
    await db.refresh(pub)
    return pub


@pytest_asyncio.fixture
async def admin_user(db) -> User:
    user = User(
        email="admin@platform.example",
        hashed_password=hash_password("adminpass123"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def advertiser_user(db, advertiser) -> User:
    user = User(
        email="advertiser@acme.example",
        hashed_password=hash_password("advertiserpass123"),
        role="advertiser",
        advertiser_id=advertiser.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def auth_headers(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    res = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def campaign_window() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return (
        (now - timedelta(days=1)).isoformat(),
        (now + timedelta(days=30)).isoformat(),
    )
