"""
Flask Dashboard — Ad Platform
Server-side rendered dashboard using Jinja2 templates + Tailwind CSS + DaisyUI.
Proxies all API calls to the FastAPI backend.
"""

from __future__ import annotations

import os
from functools import wraps
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    request as flask_request
)
from dotenv import load_dotenv
from verify_routes import verify_bp


load_dotenv()
def _require_env(name: str, min_len: int = 32) -> str:
    value = os.environ.get(name, "")
    if len(value) < min_len or "change" in value.lower():
        raise RuntimeError(
            f'{name} must be a random value of >= {min_len} chars. '
            'Generate: python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    return value

app = Flask(__name__)
app.secret_key = _require_env("FLASK_SECRET_KEY")

app.register_blueprint(verify_bp)

@app.template_filter("format_num")
def format_num(value):
    """Format a number with thousands separators."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

# ── Backend URL ───────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _headers() -> dict[str, str]:
    """Build auth headers from the session token."""
    token = session.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


def _api(method: str, path: str, **kwargs):
    """Thin wrapper around requests that raises on error."""
    url = f"{API_BASE}{path}"
    resp = requests.request(method, url, headers=_headers(), timeout=10, **kwargs)
    if resp.status_code == 401:
        session.clear()
        abort(401)
    resp.raise_for_status()
    if resp.status_code == 204:
        return None
    return resp.json()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "access_token" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated

@app.context_processor
def inject_current_path():
    return {"current_path": flask_request.path}

# ── Auth routes ───────────────────────────────────────────────────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    if "access_token" in session:
        return redirect(url_for("analytics"))

    error = None
    if request.method == "POST":
        mobile = request.form.get("mobile", "")
        password = request.form.get("password", "")
        try:
            data = _api("POST", "/auth/login", json={"mobile": mobile, "password": password})
            session["access_token"] = data["access_token"]
            session["user_mobile"] = mobile
            try:
                session["role"] = _api("GET", "/auth/me")["role"]
            except Exception:
                session["role"] = None

            return redirect(url_for("analytics"))
        except requests.HTTPError as exc:
            try:
                detail = exc.response.json().get("detail", "Login failed")
                if isinstance(detail, list):  # 422 validation error from FastAPI
                    detail = detail[0].get("msg", "Invalid mobile number").replace("Value error, ", "")
            except Exception:
                detail = "Login failed"
            error = detail
        except Exception:
            error = "Could not reach the backend. Is it running?"

    return render_template("login.html", error=error)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html", form={}, error=None)

    form = request.form
    role = form.get("role", "advertiser")
    payload = {
        "role": role,
        "organization_name": form.get("organization_name", ""),
        "mobile": form.get("mobile", ""),
        "password": form.get("password", ""),
        "email": form.get("email", ""),
    }
    if role == "publisher":
        payload["site_url"] = form.get("site_url", "")
        payload["payout_email"] = form.get("payout_email", "")
    else:
        payload["billing_email"] = form.get("email", "")

    try:
        _api("POST", "/auth/signup", json=payload)
    except requests.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", "Signup failed")
            if isinstance(detail, list):
                detail = ", ".join(str(d.get("msg", "Invalid input")).replace("Value error, ", "") for d in detail)
        except Exception:
            detail = "Signup failed"
        return render_template("signup.html", form=form, error=detail)
    except requests.RequestException:
        return render_template("signup.html", form=form, error="Could not reach the backend. Is it running?")

    flash("Account created. Verify your mobile number to sign in.", "success")
    return redirect(url_for("verify.verify_page"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ── Main pages ────────────────────────────────────────────────────────────────


@app.route("/")
@login_required
def analytics():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    try:
        stats = _api(
            "GET",
            f"/analytics/campaigns?start={quote(start.isoformat())}&end={quote(end.isoformat())}",
        )
    except Exception:
        stats = []

    totals = {
        "impressions": sum(s.get("impressions", 0) for s in stats),
        "clicks": sum(s.get("clicks", 0) for s in stats),
    }
    return render_template("analytics.html", stats=stats, totals=totals)


@app.route("/campaigns")
@login_required
def campaigns():
    try:
        campaigns_list = _api("GET", "/campaigns")
    except Exception:
        campaigns_list = []
    return render_template("campaigns.html", campaigns=campaigns_list)


@app.route("/campaigns/create", methods=["POST"])
@login_required
def create_campaign():
    payload = {
        "advertiser_id": int(request.form["advertiser_id"]),
        "name": request.form["name"],
        "priority": int(request.form.get("priority", 1)),
        # backend/app/schemas/campaign.py::CampaignCreate now also takes
        # bidding_strategy / bid_amount / total_budget, and end_date is optional.
        "bidding_strategy": request.form.get("bidding_strategy", "cpm"),
        "bid_amount": float(request.form.get("bid_amount") or 1.0),
        "daily_cap": float(request.form["daily_cap"]) if request.form.get("daily_cap") else None,
        "total_budget": float(request.form["total_budget"]) if request.form.get("total_budget") else None,
        "start_date": request.form["start_date"] + "T00:00:00Z",
    }
    if request.form.get("end_date"):
        payload["end_date"] = request.form["end_date"] + "T00:00:00Z"
    try:
        _api("POST", "/campaigns", json=payload)
        flash("Campaign created successfully.", "success")
    except Exception as exc:
        flash(f"Failed to create campaign: {exc}", "error")
    return redirect(url_for("campaigns"))


@app.route("/campaigns/<int:campaign_id>/toggle", methods=["POST"])
@login_required
def toggle_campaign(campaign_id: int):
    is_active = request.form.get("is_active") == "true"
    try:
        _api("PATCH", f"/campaigns/{campaign_id}", json={"is_active": not is_active})
    except Exception as exc:
        flash(f"Update failed: {exc}", "error")
    return redirect(url_for("campaigns"))

@app.route("/campaigns/<int:campaign_id>/creatives")
@login_required
def creatives(campaign_id: int):
    try:
        campaign = _api("GET", f"/campaigns/{campaign_id}")
        items = _api("GET", f"/creatives/by-campaign/{campaign_id}")
    except requests.HTTPError:
        flash("Could not load creatives for that campaign.", "error")
        return redirect(url_for("campaigns"))
    return render_template(
        "creatives.html",
        campaign=campaign,
        creatives=items,
        is_admin=session.get("role") == "admin",
    )


@app.route("/campaigns/<int:campaign_id>/creatives/create", methods=["POST"])
@login_required
def create_creative(campaign_id: int):
    payload = {
        "campaign_id": campaign_id,
        "name": request.form.get("name") or None,
        "asset_url": request.form["asset_url"],
        "click_url": request.form["click_url"],
        "width": int(request.form["width"]),
        "height": int(request.form["height"]),
        "format": "image",
    }
    try:
        _api("POST", "/creatives", json=payload)
        flash("Creative added. It will serve once approved.", "success")
    except Exception as exc:
        flash(f"Failed: {exc}", "error")
    return redirect(url_for("creatives", campaign_id=campaign_id))


@app.route("/campaigns/<int:campaign_id>/creatives/<int:creative_id>/toggle", methods=["POST"])
@login_required
def toggle_creative(campaign_id: int, creative_id: int):
    is_active = request.form.get("is_active") == "true"
    try:
        _api("PATCH", f"/creatives/{creative_id}", json={"is_active": not is_active})
    except Exception as exc:
        flash(f"Update failed: {exc}", "error")
    return redirect(url_for("creatives", campaign_id=campaign_id))


@app.route("/campaigns/<int:campaign_id>/creatives/<int:creative_id>/review", methods=["POST"])
@login_required
def review_creative(campaign_id: int, creative_id: int):
    decision = request.form.get("decision")
    body = {"review_status": decision}
    if decision == "rejected":
        body["rejection_reason"] = request.form.get("reason", "").strip()
    try:
        _api("PATCH", f"/creatives/{creative_id}/review", json=body)
        flash(f"Creative {decision}.", "success")
    except Exception as exc:
        flash(f"Review failed: {exc}", "error")
    return redirect(url_for("creatives", campaign_id=campaign_id))


@app.route("/campaigns/<int:campaign_id>/creatives/<int:creative_id>/delete", methods=["POST"])
@login_required
def delete_creative(campaign_id: int, creative_id: int):
    try:
        _api("DELETE", f"/creatives/{creative_id}")
        flash("Creative deleted.", "success")
    except Exception as exc:
        flash(f"Delete failed: {exc}", "error")
    return redirect(url_for("creatives", campaign_id=campaign_id))


@app.route("/campaigns/<int:campaign_id>/delete", methods=["POST"])
@login_required
def delete_campaign(campaign_id: int):
    try:
        _api("DELETE", f"/campaigns/{campaign_id}")
        flash("Campaign deleted.", "success")
    except Exception as exc:
        flash(f"Delete failed: {exc}", "error")
    return redirect(url_for("campaigns"))


@app.route("/publishers")
@login_required
def publishers():
    try:
        publishers_list = _api("GET", "/publishers")
    except Exception:
        publishers_list = []

    selected_id = request.args.get("selected", type=int)
    selected = None
    ad_units = []
    if selected_id:
        selected = next((p for p in publishers_list if p["id"] == selected_id), None)
        if selected:
            try:
                ad_units = _api("GET", f"/publishers/{selected_id}/ad-units")
            except Exception:
                ad_units = []

    return render_template(
        "publishers.html",
        publishers=publishers_list,
        selected=selected,
        ad_units=ad_units,
    )


@app.route("/publishers/create", methods=["POST"])
@login_required
def create_publisher():
    # backend/app/schemas/publisher.py::PublisherCreate requires payout_email
    # (EmailStr, no default) -- creation without it returns a 422.
    payload = {
        "name": request.form["name"],
        "site_url": request.form["site_url"],
        "payout_email": request.form["payout_email"],
    }
    if request.form.get("domain"):
        payload["domain"] = request.form["domain"]
    if request.form.get("category"):
        payload["category"] = request.form["category"]
    try:
        _api("POST", "/publishers", json=payload)
        flash("Publisher added.", "success")
    except Exception as exc:
        flash(f"Failed: {exc}", "error")
    return redirect(url_for("publishers"))


@app.route("/publishers/<int:publisher_id>/ad-units/create", methods=["POST"])
@login_required
def create_ad_unit(publisher_id: int):
    payload = {
        "publisher_id": publisher_id,
        "slot_name": request.form["slot_name"],
        "format_type": request.form.get("format_type", "display"),
        "width": int(request.form["width"]),
        "height": int(request.form["height"]),
        "reserve_price": float(request.form.get("reserve_price") or 0),
    }
    try:
        _api("POST", f"/publishers/{publisher_id}/ad-units", json=payload)
        flash("Ad slot created.", "success")
    except Exception as exc:
        flash(f"Failed: {exc}", "error")
    return redirect(url_for("publishers", selected=publisher_id))


# ── API proxy (for live analytics via JS fetch) ───────────────────────────────


@app.route("/proxy/analytics/campaigns")
@login_required
def proxy_analytics():
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    try:
        data = _api("GET", f"/analytics/campaigns?start={quote(start)}&end={quote(end)}")
        return jsonify(data)
    except Exception:
        return jsonify([])


# ── Error handlers ────────────────────────────────────────────────────────────


@app.errorhandler(401)
def unauthorized(e):
    return redirect(url_for("login"))

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_INSECURE_COOKIES") != "1",
)

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)
