from __future__ import annotations

import time

import jwt
import pytest
import pytest_asyncio
from socketio.exceptions import ConnectionRefusedError

from app.config import settings
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.sockets import dashboard_ns
from app.sockets.dashboard_ns import DashboardNamespace, emit_metric_update, emit_live_event

SID = "test-sid"


def make_user(user_id, role, *, publisher_id=None, advertiser_id=None,
              is_active=True, is_verified=True) -> User:
    return User(
        id=user_id, role=role, publisher_id=publisher_id, advertiser_id=advertiser_id,
        is_active=is_active, is_verified=is_verified, hashed_password="x",
    )


@pytest.fixture
def users(monkeypatch):
    table: dict[int, User] = {}

    async def fake_load(user_id: int):
        return table.get(user_id)

    monkeypatch.setattr(dashboard_ns, "_load_user", fake_load)
    return table


@pytest_asyncio.fixture
async def ns():
    n = DashboardNamespace("/dashboard")
    n.joined = []

    async def enter_room(sid, room, namespace=None):
        n.joined.append(room)

    n.enter_room = enter_room
    yield n
    for task in list(n._expiry_tasks.values()):
        task.cancel()


def token_for(user: User, **claims) -> str:
    return create_access_token(str(user.id), extra_claims=claims or None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth",
    [None, {}, {"token": ""}, {"token": "not-a-jwt"}, {"token": 123}, "just-a-string"],
)
async def test_missing_or_malformed_auth_refused(ns, users, auth):
    with pytest.raises(ConnectionRefusedError):
        await ns.on_connect(SID, {}, auth)
    assert ns.joined == []


@pytest.mark.asyncio
async def test_token_signed_with_wrong_secret_refused(ns, users):
    users[1] = make_user(1, UserRole.ADMIN)
    bad = jwt.encode({"sub": "1", "exp": time.time() + 60}, "other-secret-" + "x" * 40, algorithm="HS256")
    with pytest.raises(ConnectionRefusedError):
        await ns.on_connect(SID, {}, {"token": bad})


@pytest.mark.asyncio
async def test_expired_token_refused(ns, users, monkeypatch):
    users[1] = make_user(1, UserRole.ADMIN)
    monkeypatch.setattr(settings, "jwt_expires_minutes", -1)
    with pytest.raises(ConnectionRefusedError):
        await ns.on_connect(SID, {}, {"token": token_for(users[1])})


@pytest.mark.asyncio
async def test_unknown_or_inactive_user_refused(ns, users):
    users[2] = make_user(2, UserRole.ADMIN, is_active=False)
    with pytest.raises(ConnectionRefusedError):
        await ns.on_connect(SID, {}, {"token": token_for(users[2])})

    ghost = make_user(99, UserRole.ADMIN)  # valid token, but not in the "DB"
    with pytest.raises(ConnectionRefusedError):
        await ns.on_connect(SID, {}, {"token": token_for(ghost)})


@pytest.mark.asyncio
async def test_unverified_refused_when_verification_required(ns, users, monkeypatch):
    monkeypatch.setattr(settings, "require_verified_mobile", True)
    users[1] = make_user(1, UserRole.ADMIN, is_verified=False)
    with pytest.raises(ConnectionRefusedError):
        await ns.on_connect(SID, {}, {"token": token_for(users[1])})


@pytest.mark.asyncio
async def test_admin_joins_admin_room(ns, users):
    users[1] = make_user(1, UserRole.ADMIN)
    await ns.on_connect(SID, {}, {"token": token_for(users[1])})
    assert ns.joined == ["admin"]


@pytest.mark.asyncio
async def test_staff_joins_isolated_room(ns, users):
    users[4] = make_user(4, UserRole.STAFF)
    await ns.on_connect(SID, {}, {"token": token_for(users[4])})
    assert ns.joined == ["staff"]


@pytest.mark.asyncio
async def test_advertiser_joins_own_room_only(ns, users):
    users[2] = make_user(2, UserRole.ADVERTISER, advertiser_id=3)
    await ns.on_connect(SID, {}, {"token": token_for(users[2])})
    assert ns.joined == ["advertiser:3"]


@pytest.mark.asyncio
async def test_publisher_joins_own_room_only(ns, users):
    users[3] = make_user(3, UserRole.PUBLISHER, publisher_id=7)
    await ns.on_connect(SID, {}, {"token": token_for(users[3])})
    assert ns.joined == ["publisher:7"]


@pytest.mark.asyncio
async def test_role_claim_in_token_is_ignored(ns, users):
    users[2] = make_user(2, UserRole.ADVERTISER, advertiser_id=3)
    await ns.on_connect(SID, {}, {"token": token_for(users[2], role="admin")})
    assert ns.joined == ["advertiser:3"]  # not "admin"


@pytest.mark.asyncio
async def test_expiry_task_scheduled_and_cancelled_on_disconnect(ns, users):
    users[1] = make_user(1, UserRole.ADMIN)
    await ns.on_connect(SID, {}, {"token": token_for(users[1])})
    task = ns._expiry_tasks[SID]

    await ns.on_disconnect(SID)
    assert SID not in ns._expiry_tasks
    await __import__("asyncio").sleep(0)  # let the cancellation land
    assert task.cancelled()


@pytest.mark.asyncio
async def test_socket_disconnected_when_token_expires(ns):
    disconnected = []

    async def fake_disconnect(sid, namespace=None):
        disconnected.append(sid)

    ns.disconnect = fake_disconnect
    await ns._disconnect_at_expiry(SID, 0)
    assert disconnected == [SID]


class FakeSio:
    def __init__(self):
        self.emitted = []

    async def emit(self, event, data, room=None, namespace=None):
        self.emitted.append((event, data, room, namespace))


@pytest.mark.asyncio
async def test_metric_update_targets_only_owning_rooms(monkeypatch):
    fake = FakeSio()
    monkeypatch.setattr(dashboard_ns, "_sio", fake)

    await emit_metric_update({"type": "impression"}, advertiser_id=3, publisher_id=7)

    assert [e[2] for e in fake.emitted] == ["admin", "advertiser:3", "publisher:7"]
    assert all(e[0] == "metric_update" and e[3] == "/dashboard" for e in fake.emitted)


@pytest.mark.asyncio
async def test_metric_update_never_broadcasts_unscoped(monkeypatch):
    fake = FakeSio()
    monkeypatch.setattr(dashboard_ns, "_sio", fake)

    await emit_metric_update({"type": "click"})  # no owner ids

    assert [e[2] for e in fake.emitted] == ["admin"]

@pytest.mark.asyncio
async def test_live_event_goes_to_admin_room_only(monkeypatch):
    fake = FakeSio()
    monkeypatch.setattr(dashboard_ns, "_sio", fake)

    await emit_live_event({"id": 1, "type": "click"})

    assert [(e[0], e[2]) for e in fake.emitted] == [("live_event", "admin")]    
