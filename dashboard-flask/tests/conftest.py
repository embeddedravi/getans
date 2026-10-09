"""Shared fixtures: the Flask app, a fake FastAPI backend, and logged-in clients.

Nothing here talks to a real backend. `requests.request` and `requests.post`
are patched, so every call the dashboard makes lands in `FakeBackend`.
"""

from __future__ import annotations

import os

# Must be set before `app` is imported: it validates the secret and reads the
# cookie flag at import time.
os.environ["FLASK_SECRET_KEY"] = "test-only-secret-" + "x" * 40
os.environ["FLASK_INSECURE_COOKIES"] = "1"  # test client talks plain HTTP
os.environ["API_BASE_URL"] = "http://backend.test/api"

import pytest
import requests

import app as app_module  # dashboard-flask/app.py (pytest.ini puts the folder on sys.path)

API_BASE = app_module.API_BASE


class FakeResponse:
    def __init__(self, status: int = 200, body=None):
        self.status_code = status
        self._body = body

    @property
    def ok(self) -> bool:
        return self.status_code < 400

    def json(self):
        if self._body is None:
            raise ValueError("no JSON body")
        return self._body

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


class FakeBackend:
    """Routes (method, path) to canned responses and records every call."""

    def __init__(self):
        self.routes: dict[tuple[str, str], object] = {}
        self.calls: list[dict] = []
        self.users_by_token: dict[str, dict] = {}
        self.user = {"id": 1, "role": "advertiser", "mobile": "+919123456789", "email": None,
                     "first_name": None, "last_name": None}

    def on(self, method: str, path: str, body=None, status: int = 200):
        """Register a response. `body` may be a callable taking the recorded call."""
        self.routes[(method, path)] = (status, body)

    def fail(self, method: str, path: str, exc: Exception):
        self.routes[(method, path)] = exc

    def request(self, method, url, **kwargs):
        path = url[len(API_BASE):].split("?")[0]
        call = {
            "method": method, "path": path,
            "headers": kwargs.get("headers"), "json": kwargs.get("json"),
            "data": kwargs.get("data"), "files": None,
        }
        files = kwargs.get("files")
        if files:
            name, stream, mimetype = files["file"]
            call["files"] = {"filename": name, "mimetype": mimetype, "content": stream.read()}
        self.calls.append(call)

        route = self.routes.get((method, path))
        if isinstance(route, Exception):
            raise route
        if route is None:
            if (method, path) == ("GET", "/auth/me"):
                token = (kwargs.get("headers") or {}).get("Authorization", "").removeprefix("Bearer ")
                return FakeResponse(200, self.users_by_token.get(token, self.user))
            if (method, path) == ("GET", "/admin/approvals/pending"):
                return FakeResponse(200, {"publishers": [], "advertisers": [], "ad_units": []})
            return FakeResponse(404, {"detail": "Not found"})

        if isinstance(route, list):          # sequence: one (status, body) per call
            route = route.pop(0)
        status, body = route
        
        return FakeResponse(status, body(call) if callable(body) else body)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def calls_to(self, method: str, path: str) -> list[dict]:
        return [c for c in self.calls if c["method"] == method and c["path"] == path]


@pytest.fixture
def flask_app():
    app_module.app.config.update(TESTING=True)
    return app_module.app


@pytest.fixture
def backend(monkeypatch):
    fake = FakeBackend()
    monkeypatch.setattr(requests, "request", fake.request)
    monkeypatch.setattr(requests, "post", fake.post)
    return fake


def _logged_in(flask_app, backend, role: str):
    token = "tok" if role == "advertiser" else f"tok-{role}"
    backend.users_by_token[token] = {**backend.user, "role": role}
    client = flask_app.test_client()
    with client.session_transaction() as s:
        s["access_token"] = token
        s["role"] = role
        s["user_id"] = 1
    return client


@pytest.fixture
def anon(flask_app, backend):
    return flask_app.test_client()


@pytest.fixture
def advertiser(flask_app, backend):
    return _logged_in(flask_app, backend, "advertiser")


@pytest.fixture
def admin(flask_app, backend):
    return _logged_in(flask_app, backend, "admin")
