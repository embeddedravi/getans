from __future__ import annotations

import pytest

from tests.conftest import auth_headers, campaign_window


@pytest.mark.asyncio
async def test_create_campaign_requires_auth(client, advertiser):
    start, end = campaign_window()
    res = await client.post(
        "/api/campaigns",
        json={
            "advertiser_id": advertiser.id,
            "name": "Summer sale",
            "start_date": start,
            "end_date": end,
        },
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_admin_can_create_and_fetch_campaign(client, admin_user, advertiser):
    headers = await auth_headers(client, "admin@platform.example", "adminpass123")
    start, end = campaign_window()

    create_res = await client.post(
        "/api/campaigns",
        json={
            "advertiser_id": advertiser.id,
            "name": "Summer sale",
            "priority": 5,
            "start_date": start,
            "end_date": end,
        },
        headers=headers,
    )
    assert create_res.status_code == 201, create_res.text
    campaign_id = create_res.json()["id"]

    get_res = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Summer sale"
    assert get_res.json()["priority"] == 5


@pytest.mark.asyncio
async def test_end_date_before_start_date_rejected(client, admin_user, advertiser):
    headers = await auth_headers(client, "admin@platform.example", "adminpass123")
    start, end = campaign_window()

    res = await client.post(
        "/api/campaigns",
        json={
            "advertiser_id": advertiser.id,
            "name": "Broken window",
            "start_date": end,  # swapped on purpose
            "end_date": start,
        },
        headers=headers,
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_advertiser_cannot_create_campaign_for_other_advertiser(
    client, advertiser_user, db
):
    from app.models.advertiser import Advertiser

    other = Advertiser(name="Other Co", billing_email="billing@other.example")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    headers = await auth_headers(client, "advertiser@acme.example", "advertiserpass123")
    start, end = campaign_window()

    res = await client.post(
        "/api/campaigns",
        json={
            "advertiser_id": other.id,
            "name": "Sneaky campaign",
            "start_date": start,
            "end_date": end,
        },
        headers=headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_advertiser_only_sees_own_campaigns(client, admin_user, advertiser_user, advertiser, db):
    from app.models.advertiser import Advertiser
    from app.models.campaign import Campaign

    other = Advertiser(name="Other Co", billing_email="billing@other.example")
    db.add(other)
    await db.commit()
    await db.refresh(other)

    start, end = campaign_window()
    admin_headers = await auth_headers(client, "admin@platform.example", "adminpass123")

    await client.post(
        "/api/campaigns",
        json={"advertiser_id": advertiser.id, "name": "Mine", "start_date": start, "end_date": end},
        headers=admin_headers,
    )
    await client.post(
        "/api/campaigns",
        json={"advertiser_id": other.id, "name": "Not mine", "start_date": start, "end_date": end},
        headers=admin_headers,
    )

    advertiser_headers = await auth_headers(client, "advertiser@acme.example", "advertiserpass123")
    res = await client.get("/api/campaigns", headers=advertiser_headers)

    assert res.status_code == 200
    names = [c["name"] for c in res.json()]
    assert names == ["Mine"]


@pytest.mark.asyncio
async def test_update_and_delete_campaign(client, admin_user, advertiser):
    headers = await auth_headers(client, "admin@platform.example", "adminpass123")
    start, end = campaign_window()

    create_res = await client.post(
        "/api/campaigns",
        json={
            "advertiser_id": advertiser.id,
            "name": "Original name",
            "start_date": start,
            "end_date": end,
        },
        headers=headers,
    )
    campaign_id = create_res.json()["id"]

    patch_res = await client.patch(
        f"/api/campaigns/{campaign_id}",
        json={"is_active": False, "name": "Paused campaign"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_active"] is False
    assert patch_res.json()["name"] == "Paused campaign"

    delete_res = await client.delete(f"/api/campaigns/{campaign_id}", headers=headers)
    assert delete_res.status_code == 204

    get_res = await client.get(f"/api/campaigns/{campaign_id}", headers=headers)
    assert get_res.status_code == 404
