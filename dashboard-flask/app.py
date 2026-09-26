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
)
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")


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


# ── Auth routes ───────────────────────────────────────────────────────────────


@app.route("/login", methods=["GET", "POST"])
def login():
    if "access_token" in session:
        return redirect(url_for("analytics"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        try:
            data = _api("POST", "/auth/login", json={"email": email, "password": password})
            session["access_token"] = data["access_token"]
            session["user_email"] = email
            return redirect(url_for("analytics"))
        except requests.HTTPError as exc:
            try:
                detail = exc.response.json().get("detail", "Login failed")
            except Exception:
                detail = "Login failed"
            error = detail
        except Exception:
            error = "Could not reach the backend. Is it running?"

    return render_template("login.html", error=error)


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
        "daily_cap": float(request.form["daily_cap"]) if request.form.get("daily_cap") else None,
        "start_date": request.form["start_date"] + "T00:00:00Z",
        "end_date": request.form["end_date"] + "T00:00:00Z",
    }
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
    payload = {"name": request.form["name"], "site_url": request.form["site_url"]}
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
        "width": int(request.form["width"]),
        "height": int(request.form["height"]),
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
