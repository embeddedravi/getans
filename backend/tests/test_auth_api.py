from __future__ import annotations

import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    res = await client.post(
        "/api/auth/login", json={"mobile": "9876543210", "password": "adminpass123"}
    )
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"


@pytest.mark.asyncio
@pytest.mark.parametrize("mobile", ["+91 98765 43210", "09876543210", "919876543210"])
async def test_login_accepts_common_formats(client, admin_user, mobile):
    res = await client.post("/api/auth/login", json={"mobile": mobile, "password": "adminpass123"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    res = await client.post(
        "/api/auth/login", json={"mobile": "9876543210", "password": "wrongpass1"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_mobile(client):
    res = await client.post(
        "/api/auth/login", json={"mobile": "9000000000", "password": "whatever123"}
    )
    assert res.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("mobile", ["12345", "5876543210", "98765abcde"])
async def test_login_rejects_invalid_mobile(client, mobile):
    res = await client.post("/api/auth/login", json={"mobile": mobile, "password": "whatever123"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_me_requires_token(client):
    assert (await client.get("/api/auth/me")).status_code == 401


@pytest.mark.asyncio
async def test_me_returns_current_user(client, admin_user):
    headers = await auth_headers(client, "9876543210", "adminpass123")
    res = await client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["mobile"] == "+919876543210"
    assert res.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_register_without_email(client, admin_user):
    headers = await auth_headers(client, "9876543210", "adminpass123")
    res = await client.post(
        "/api/auth/register",
        json={"mobile": "98111 22333", "password": "newuserpass1", "role": "admin", "email": ""},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["mobile"] == "+919811122333"
    assert res.json()["email"] is None

    login = await client.post(
        "/api/auth/login", json={"mobile": "9811122333", "password": "newuserpass1"}
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_register_duplicate_mobile_conflicts(client, admin_user):
    headers = await auth_headers(client, "9876543210", "adminpass123")
    res = await client.post(
        "/api/auth/register",
        json={"mobile": "+919876543210", "password": "newuserpass1", "role": "admin"},
        headers=headers,
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_requires_admin(client, advertiser_user):
    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    res = await client.post(
        "/api/auth/register",
        json={"mobile": "9811122333", "password": "newuserpass1", "role": "admin"},
        headers=headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_password_reset_requires_valid_otp_and_updates_credentials(client, admin_user, monkeypatch):
    async def invalid_otp(db, mobile, code):
        return False

    monkeypatch.setattr("app.api.auth.verify_otp", invalid_otp)
    payload = {"mobile": "9876543210", "code": "123456", "password": "newpassword1"}
    rejected = await client.post("/api/auth/forgot-password/reset", json=payload)
    assert rejected.status_code == 400

    async def valid_otp(db, mobile, code):
        assert mobile == "+919876543210"
        return True

    monkeypatch.setattr("app.api.auth.verify_otp", valid_otp)
    reset = await client.post("/api/auth/forgot-password/reset", json=payload)
    assert reset.status_code == 200
    login = await client.post("/api/auth/login", json={"mobile": "9876543210", "password": "newpassword1"})
    assert login.status_code == 200
