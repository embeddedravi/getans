from __future__ import annotations

import io

import pytest
from PIL import Image

from app.config import settings
from tests.conftest import auth_headers, campaign_window


def png_bytes(w=300, h=250) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "red").save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _media_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "media_dir", tmp_path)


@pytest.mark.asyncio
async def test_upload_list_and_create_creative_from_media(client, db, advertiser, advertiser_user):
    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    res = await client.post("/api/media", headers=headers,
                            files={"file": ("banner.png", png_bytes(), "image/png")})
    assert res.status_code == 201, res.text
    media = res.json()
    assert (media["width"], media["height"], media["kind"]) == (300, 250, "image")
    assert (await client.get("/api/media", headers=headers)).json()[0]["id"] == media["id"]

    start, end = campaign_window()
    camp = await client.post("/api/campaigns", headers=headers, json={
        "advertiser_id": advertiser.id, "name": "Campaign", "start_date": start, "end_date": end})
    assert camp.status_code == 201, camp.text
    cr = await client.post("/api/creatives", headers=headers, json={
        "campaign_id": camp.json()["id"], "media_id": media["id"], "click_url": "https://example.com"})
    assert cr.status_code == 201, cr.text
    assert cr.json()["width"] == 300 and cr.json()["asset_url"] == media["url"]

    # in use -> cannot delete
    assert (await client.delete(f"/api/media/{media['id']}", headers=headers)).status_code == 409


@pytest.mark.asyncio
async def test_rejects_non_media_and_spoofed_content_type(client, advertiser_user):
    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    res = await client.post("/api/media", headers=headers,
                            files={"file": ("evil.png", b"<svg onload=alert(1)>", "image/png")})
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_size_limit_and_tenant_isolation(client, db, advertiser_user, admin_user, monkeypatch):
    monkeypatch.setattr(settings, "media_max_image_mb", 0)
    headers = await auth_headers(client, "9123456789", "advertiserpass123")
    res = await client.post("/api/media", headers=headers,
                            files={"file": ("a.png", png_bytes(), "image/png")})
    assert res.status_code == 413
    admin = await auth_headers(client, "9876543210", "adminpass123")
    assert (await client.post("/api/media", headers=admin,
                              files={"file": ("a.png", png_bytes(), "image/png")})).status_code == 403
