from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    res = await client.post(
        "/api/auth/login",
        json={"email": "admin@platform.example", "password": "adminpass123"},
    )

    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    res = await client.post(
        "/api/auth/login",
        json={"email": "admin@platform.example", "password": "wrong"},
    )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client):
    res = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )

    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client):
    res = await client.get("/api/auth/me")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client, admin_user):
    login = await client.post(
        "/api/auth/login",
        json={"email": "admin@platform.example", "password": "adminpass123"},
    )
    token = login.json()["access_token"]

    res = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert res.json()["email"] == "admin@platform.example"
    assert res.json()["role"] == "admin"
