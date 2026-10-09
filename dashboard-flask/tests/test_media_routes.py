from __future__ import annotations

import io

import pytest
import requests

IMAGE = {"id": 5, "advertiser_id": 7, "kind": "image", "original_filename": "banner.png",
         "content_type": "image/png", "size_bytes": 2_097_152, "width": 300, "height": 250,
         "duration_seconds": None, "url": "http://cdn.test/uploads/aaa.png",
         "created_at": "2026-10-01T00:00:00Z"}
VIDEO = {**IMAGE, "id": 6, "kind": "video", "original_filename": "promo.mp4",
         "content_type": "video/mp4", "width": 728, "height": 90, "duration_seconds": "12.50",
         "url": "http://cdn.test/uploads/bbb.mp4"}


def text(resp) -> str:
    return resp.get_data(as_text=True)


def upload(client, *files, **form):
    """files are (name, bytes, mimetype) tuples."""
    data = {"files": [(io.BytesIO(b), n, m) for n, b, m in files], **form}
    return client.post("/media/upload", data=data, content_type="multipart/form-data",
                       follow_redirects=True)


# ── access control ───────────────────────────────────────────────────────────

ROUTES = [
    ("GET", "/media"),
    ("POST", "/media/upload"),
    ("POST", "/media/5/delete"),
    ("POST", "/campaigns/3/creatives/create-from-media"),
]


@pytest.mark.parametrize("method,path", ROUTES)
def test_anonymous_users_are_sent_to_login(anon, method, path):
    resp = anon.open(path, method=method)
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]


@pytest.mark.parametrize("method,path", ROUTES[:3])
def test_media_pages_are_advertiser_only(admin, backend, method, path):
    assert admin.open(path, method=method).status_code == 403
    assert backend.calls_to("POST", "/media") == []


def test_delete_rejects_get(advertiser):
    assert advertiser.get("/media/5/delete").status_code == 405


# ── library page ─────────────────────────────────────────────────────────────

def test_library_renders_images_and_videos(advertiser, backend):
    backend.on("GET", "/media", [IMAGE, VIDEO])
    html = text(advertiser.get("/media"))
    assert "banner.png" in html and "promo.mp4" in html
    assert 'src="http://cdn.test/uploads/aaa.png"' in html
    assert "<video" in html and "bbb.mp4" in html
    assert "300×250" in html and "2.00 MB" in html
    assert "13s" in html or "12s" in html  # duration shown, rounded
    assert 'action="/media/5/delete"' in html


def test_library_empty_state(advertiser, backend):
    backend.on("GET", "/media", [])
    assert "No media yet" in text(advertiser.get("/media"))


def test_library_backend_error_is_flashed(advertiser, backend):
    backend.on("GET", "/media", {"detail": "boom"}, status=500)
    html = text(advertiser.get("/media"))
    assert "Could not load media" in html and "No media yet" in html


def test_advertiser_sees_media_link_in_sidebar_and_admin_does_not(advertiser, admin):
    assert 'href="/media"' in text(advertiser.get("/"))
    assert 'href="/media"' not in text(admin.get("/"))


# ── upload ───────────────────────────────────────────────────────────────────

def test_upload_without_files_does_not_call_backend(advertiser, backend):
    resp = advertiser.post("/media/upload", data={}, content_type="multipart/form-data",
                           follow_redirects=True)
    assert "Choose at least one file" in text(resp)
    assert backend.calls_to("POST", "/media") == []


def test_upload_forwards_each_file_with_bearer_token_only(advertiser, backend):
    backend.on("POST", "/media", IMAGE, status=201)
    backend.on("GET", "/media", [IMAGE])
    resp = upload(advertiser,
                  ("a.png", b"png-bytes", "image/png"),
                  ("b.mp4", b"mp4-bytes", "video/mp4"))

    calls = backend.calls_to("POST", "/media")
    assert [c["files"]["filename"] for c in calls] == ["a.png", "b.mp4"]
    assert calls[0]["files"]["content"] == b"png-bytes"
    assert calls[1]["files"]["mimetype"] == "video/mp4"
    # No JSON Content-Type: requests must set the multipart boundary itself.
    assert all(c["headers"] == {"Authorization": "Bearer tok"} for c in calls)
    assert "Uploaded 2 files." in text(resp)


def test_upload_single_file_message_is_singular(advertiser, backend):
    backend.on("POST", "/media", IMAGE, status=201)
    assert "Uploaded 1 file." in text(upload(advertiser, ("a.png", b"x", "image/png")))


def test_video_dimensions_are_forwarded_only_when_given(advertiser, backend):
    backend.on("POST", "/media", VIDEO, status=201)
    upload(advertiser, ("v.mp4", b"x", "video/mp4"), width="728", height="90")
    upload(advertiser, ("v.mp4", b"x", "video/mp4"), width="", height="")
    first, second = backend.calls_to("POST", "/media")
    assert first["data"] == {"width": "728", "height": "90"}
    assert second["data"] == {}


def test_partial_failure_reports_success_and_each_error(advertiser, backend):
    backend.routes[("POST", "/media")] = [
        (201, IMAGE),
        (415, {"detail": "Unsupported file. Use PNG, JPEG."}),
    ]
    html = text(upload(advertiser, ("ok.png", b"x", "image/png"), ("bad.txt", b"y", "text/plain")))
    assert "Uploaded 1 file." in html
    assert "bad.txt: Unsupported file" in html


def test_validation_list_detail_is_cleaned_up(advertiser, backend):
    backend.on("POST", "/media",
               {"detail": [{"msg": "Value error, Video too long"}, {"msg": "Field required"}]},
               status=422)
    html = text(upload(advertiser, ("v.mp4", b"x", "video/mp4")))
    assert "v.mp4: Video too long, Field required" in html
    assert "Value error" not in html
    assert "Uploaded" not in html


def test_unreachable_backend_is_reported_per_file(advertiser, backend):
    backend.fail("POST", "/media", requests.ConnectionError("down"))
    html = text(upload(advertiser, ("a.png", b"x", "image/png")))
    assert "a.png: could not reach the backend" in html


def test_expired_token_clears_session_and_redirects(advertiser, backend):
    backend.on("POST", "/media", {"detail": "Could not validate credentials"}, status=401)
    resp = advertiser.post(
        "/media/upload",
        data={"files": [(io.BytesIO(b"x"), "a.png", "image/png")]},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]
    with advertiser.session_transaction() as s:
        assert "access_token" not in s


def test_oversized_request_gets_friendly_message(advertiser, backend, flask_app, monkeypatch):
    monkeypatch.setitem(flask_app.config, "MAX_CONTENT_LENGTH", 1000)
    resp = upload(advertiser, ("big.mp4", b"x" * 10_000, "video/mp4"))
    assert "Upload too large" in text(resp)
    assert backend.calls_to("POST", "/media") == []


# ── delete ───────────────────────────────────────────────────────────────────

def test_delete_calls_backend_and_confirms(advertiser, backend):
    backend.on("DELETE", "/media/5", None, status=204)
    resp = advertiser.post("/media/5/delete", follow_redirects=True)
    assert len(backend.calls_to("DELETE", "/media/5")) == 1
    assert "Media deleted." in text(resp)


def test_delete_shows_backend_reason_when_in_use(advertiser, backend):
    backend.on("DELETE", "/media/5",
               {"detail": "Used by 2 creative(s). Delete those creatives first."}, status=409)
    html = text(advertiser.post("/media/5/delete", follow_redirects=True))
    assert "Used by 2 creative(s)" in html
    assert "Media deleted." not in html


# ── creatives: media picker ──────────────────────────────────────────────────

CAMPAIGN = {"id": 3, "name": "Autumn sale", "advertiser_id": 7}


def _creative(**over):
    return {"id": 10, "campaign_id": 3, "name": "Clip", "asset_url": "http://cdn.test/uploads/c.png",
            "click_url": "https://example.com", "width": 300, "height": 250, "format": "image",
            "review_status": "pending", "rejection_reason": None, "is_active": True, **over}


def test_picker_lists_only_the_campaign_owners_media(admin, backend):
    other = {**IMAGE, "id": 9, "advertiser_id": 8, "original_filename": "someone-elses.png"}
    backend.on("GET", "/campaigns/3", CAMPAIGN)
    backend.on("GET", "/creatives/by-campaign/3", [])
    backend.on("GET", "/media", [IMAGE, other])
    html = text(admin.get("/campaigns/3/creatives"))
    assert "banner.png (image, 300×250)" in html
    assert "someone-elses.png" not in html
    assert 'action="/campaigns/3/creatives/create-from-media"' in html


def test_picker_points_to_library_when_empty(advertiser, backend):
    backend.on("GET", "/campaigns/3", CAMPAIGN)
    backend.on("GET", "/creatives/by-campaign/3", [])
    backend.on("GET", "/media", [])
    html = text(advertiser.get("/campaigns/3/creatives"))
    assert "Upload an image or video" in html and 'href="/media"' in html


def test_page_still_loads_if_media_listing_fails(advertiser, backend):
    backend.on("GET", "/campaigns/3", CAMPAIGN)
    backend.on("GET", "/creatives/by-campaign/3", [_creative()])
    backend.on("GET", "/media", {"detail": "boom"}, status=500)
    resp = advertiser.get("/campaigns/3/creatives")
    assert resp.status_code == 200 and "Clip" in text(resp)


def test_video_creatives_preview_with_video_tag(advertiser, backend):
    backend.on("GET", "/campaigns/3", CAMPAIGN)
    backend.on("GET", "/creatives/by-campaign/3",
               [_creative(format="video", asset_url="http://cdn.test/uploads/c.mp4")])
    backend.on("GET", "/media", [])
    html = text(advertiser.get("/campaigns/3/creatives"))
    assert '<video src="http://cdn.test/uploads/c.mp4"' in html


# ── creatives: create from media ─────────────────────────────────────────────

def test_create_from_media_sends_expected_payload(advertiser, backend):
    backend.on("POST", "/creatives", {"id": 11}, status=201)
    resp = advertiser.post("/campaigns/3/creatives/create-from-media",
                           data={"media_id": "5", "name": "", "click_url": "https://example.com/x"})
    assert resp.status_code == 302 and resp.headers["Location"].endswith("/campaigns/3/creatives")
    (call,) = backend.calls_to("POST", "/creatives")
    assert call["json"] == {"campaign_id": 3, "media_id": 5, "name": None,
                            "click_url": "https://example.com/x"}


def test_create_from_media_flashes_success(advertiser, backend):
    backend.on("POST", "/creatives", {"id": 11}, status=201)
    for path in ("/campaigns/3/creatives", "/campaigns/3"):
        backend.on("GET", path, CAMPAIGN if path.endswith("3") else [])
    backend.on("GET", "/creatives/by-campaign/3", [])
    backend.on("GET", "/media", [])
    resp = advertiser.post("/campaigns/3/creatives/create-from-media",
                           data={"media_id": "5", "click_url": "https://example.com"},
                           follow_redirects=True)
    assert "Creative created" in text(resp)


@pytest.mark.parametrize("form", [{"click_url": "https://example.com"},
                                  {"media_id": "abc", "click_url": "https://example.com"}])
def test_create_from_media_requires_a_valid_media_id(advertiser, backend, form):
    resp = advertiser.post("/campaigns/3/creatives/create-from-media", data=form)
    assert resp.status_code == 302
    assert backend.calls_to("POST", "/creatives") == []
    with advertiser.session_transaction() as s:
        assert ("error", "Choose an image or video first.") in s["_flashes"]


def test_create_from_media_shows_backend_reason(advertiser, backend):
    backend.on("POST", "/creatives", {"detail": "Media asset not found"}, status=404)
    with advertiser.session_transaction():
        pass
    advertiser.post("/campaigns/3/creatives/create-from-media",
                    data={"media_id": "99", "click_url": "https://example.com"})
    with advertiser.session_transaction() as s:
        assert ("error", "Failed: Media asset not found") in s["_flashes"]