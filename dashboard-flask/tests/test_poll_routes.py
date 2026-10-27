def test_poll_management_lists_only_poll_creatives(advertiser, backend):
    campaign = {"id": 3, "name": "Autumn sale", "advertiser_id": 7}
    poll = {
        "id": 11, "campaign_id": 3, "name": "Cloud poll", "format": "poll",
        "custom_attributes": {"poll_question": "Which cloud do you use?", "poll_options": ["A", "B", "C", "D"]},
        "review_status": "approved", "is_active": True,
    }
    backend.on("GET", "/campaigns", [campaign])
    backend.on("GET", "/creatives/polls", [{"creative": poll, "campaign": {"id": 3, "name": "Autumn sale"}}])

    response = advertiser.get("/poll")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Which cloud do you use?" in html
    assert "Cloud poll" in html
    assert "Banner" not in html


def test_create_poll_from_management_posts_validated_poll(advertiser, backend):
    backend.on("POST", "/creatives", {"id": 11}, status=201)

    response = advertiser.post("/poll/create", data={
        "campaign_id": "3",
        "name": "Cloud poll",
        "poll_question": "Which cloud do you use?",
        "option_1": "AWS", "option_2": "Azure", "option_3": "GCP", "option_4": "Other",
        "click_url": "https://example.com",
    })

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/poll")
    (call,) = backend.calls_to("POST", "/creatives")
    assert call["json"]["format"] == "poll"
    assert call["json"]["poll_options"] == ["AWS", "Azure", "GCP", "Other"]


def test_poll_management_is_not_available_to_publishers(flask_app, backend):
    from conftest import _logged_in

    publisher = _logged_in(flask_app, backend, "publisher")
    assert publisher.get("/poll").status_code == 403


def test_admin_can_review_poll_from_campaign_creatives(admin, backend):
    campaign = {"id": 3, "name": "Autumn sale", "advertiser_id": 7}
    poll = {
        "id": 11, "campaign_id": 3, "name": "Cloud poll", "format": "poll",
        "asset_url": "https://example.com/poll.png", "click_url": "https://example.com",
        "width": 300, "height": 250, "review_status": "pending", "is_active": True,
        "custom_attributes": {"poll_question": "Which cloud do you use?", "poll_options": ["A", "B", "C", "D"]},
    }
    backend.on("GET", "/campaigns/3", campaign)
    backend.on("GET", "/creatives/by-campaign/3", [poll])
    backend.on("GET", "/media", [])
    page = admin.get("/campaigns/3/creatives")
    assert b"Approve" in page.data and b"Reject" in page.data

    backend.on("PATCH", "/creatives/11/review", {**poll, "review_status": "approved"})
    response = admin.post("/campaigns/3/creatives/11/review", data={"decision": "approved"})

    assert response.status_code == 302
    (call,) = backend.calls_to("PATCH", "/creatives/11/review")
    assert call["json"] == {"review_status": "approved"}


def test_admin_can_review_poll_from_poll_management(admin, backend):
    campaign = {"id": 3, "name": "Autumn sale", "advertiser_id": 7}
    poll = {
        "id": 11, "campaign_id": 3, "name": "Cloud poll", "format": "poll",
        "review_status": "pending", "is_active": True,
        "custom_attributes": {"poll_question": "Which cloud?"},
    }
    backend.on("GET", "/campaigns", [campaign])
    backend.on("GET", "/creatives/polls", [{"creative": poll, "campaign": {"id": 3, "name": "Autumn sale"}}])
    page = admin.get("/poll")
    assert b"Moderation" in page.data and b"Approve" in page.data and b"Reject" in page.data

    backend.on("PATCH", "/creatives/11/review", {**poll, "review_status": "approved"})
    response = admin.post("/poll/11/review", data={"decision": "approved"})
    assert response.status_code == 302
    (call,) = backend.calls_to("PATCH", "/creatives/11/review")
    assert call["json"] == {"review_status": "approved"}
