from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.publisher import Publisher
from app.models.user import User
from tests.conftest import auth_headers

ADMIN = ("9876543210", "adminpass123")
PUB_USER = ("9811122333", "publisherpass1")


@pytest_asyncio.fixture
async def funded_publisher(db) -> Publisher:
    pub = Publisher(
        name="Example News",
        site_url="https://news.example.com",
        payout_email="pay@news.example.com",
        unpaid_earnings=Decimal("100.00"),
    )
    db.add(pub)
    await db.commit()
    await db.refresh(pub)
    return pub


@pytest_asyncio.fixture
async def publisher_user(db, funded_publisher) -> User:
    user = User(
        mobile="+919811122333",
        hashed_password=hash_password(PUB_USER[1]),
        role="publisher",
        publisher_id=funded_publisher.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _create(client, headers, publisher_id, amount="40.00"):
    return await client.post(
        "/api/payouts", json={"publisher_id": publisher_id, "amount": amount}, headers=headers
    )


@pytest.mark.asyncio
async def test_create_requires_admin(client, admin_user, publisher_user, funded_publisher):
    headers = await auth_headers(client, *PUB_USER)
    assert (await _create(client, headers, funded_publisher.id)).status_code == 403


@pytest.mark.asyncio
async def test_create_snapshots_email_and_starts_pending(client, admin_user, funded_publisher):
    headers = await auth_headers(client, *ADMIN)
    res = await _create(client, headers, funded_publisher.id)
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "pending"
    assert res.json()["payout_email"] == "pay@news.example.com"


@pytest.mark.asyncio
async def test_open_payouts_count_against_available_balance(client, admin_user, funded_publisher):
    headers = await auth_headers(client, *ADMIN)
    assert (await _create(client, headers, funded_publisher.id, "70.00")).status_code == 201
    # 100 unpaid - 70 reserved = 30 available
    assert (await _create(client, headers, funded_publisher.id, "40.00")).status_code == 409
    assert (await _create(client, headers, funded_publisher.id, "30.00")).status_code == 201


@pytest.mark.asyncio
async def test_unknown_publisher_404(client, admin_user):
    headers = await auth_headers(client, *ADMIN)
    assert (await _create(client, headers, 9999)).status_code == 404


@pytest.mark.asyncio
async def test_marking_paid_decrements_unpaid_earnings(client, admin_user, funded_publisher, db):
    headers = await auth_headers(client, *ADMIN)
    payout_id = (await _create(client, headers, funded_publisher.id, "40.00")).json()["id"]

    res = await client.patch(
        f"/api/payouts/{payout_id}",
        json={"status": "paid", "reference": "txn_123"},
        headers=headers,
    )
    assert res.status_code == 200, res.text
    assert res.json()["paid_at"] is not None

    await db.refresh(funded_publisher)
    assert funded_publisher.unpaid_earnings == Decimal("60.00")


@pytest.mark.asyncio
async def test_failed_requires_reason_and_frees_balance(client, admin_user, funded_publisher):
    headers = await auth_headers(client, *ADMIN)
    payout_id = (await _create(client, headers, funded_publisher.id, "100.00")).json()["id"]

    bad = await client.patch(f"/api/payouts/{payout_id}", json={"status": "failed"}, headers=headers)
    assert bad.status_code == 400

    ok = await client.patch(
        f"/api/payouts/{payout_id}",
        json={"status": "failed", "failure_reason": "Bank rejected"},
        headers=headers,
    )
    assert ok.status_code == 200
    # Balance is available again.
    assert (await _create(client, headers, funded_publisher.id, "100.00")).status_code == 201


@pytest.mark.asyncio
async def test_terminal_payout_is_immutable(client, admin_user, funded_publisher):
    headers = await auth_headers(client, *ADMIN)
    payout_id = (await _create(client, headers, funded_publisher.id)).json()["id"]
    await client.patch(f"/api/payouts/{payout_id}", json={"status": "cancelled"}, headers=headers)

    res = await client.patch(f"/api/payouts/{payout_id}", json={"status": "paid"}, headers=headers)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_publisher_sees_only_own_payouts(client, admin_user, publisher_user, funded_publisher, db):
    other = Publisher(name="Other", site_url="https://o.example.com",
                      payout_email="o@example.com", unpaid_earnings=Decimal("50.00"))
    db.add(other)
    await db.commit()
    await db.refresh(other)

    admin_headers = await auth_headers(client, *ADMIN)
    mine = (await _create(client, admin_headers, funded_publisher.id)).json()["id"]
    theirs = (await _create(client, admin_headers, other.id, "10.00")).json()["id"]

    headers = await auth_headers(client, *PUB_USER)
    listed = await client.get("/api/payouts", headers=headers)
    assert [p["id"] for p in listed.json()] == [mine]
    assert (await client.get(f"/api/payouts/{theirs}", headers=headers)).status_code == 403
    assert (await client.get(f"/api/payouts/{mine}", headers=headers)).status_code == 200