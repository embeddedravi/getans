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
        
@app.template_filter("inr")
def inr(value, places=2):
    try:
        return f"₹{float(value):,.{places}f}"
    except (TypeError, ValueError):
        return "—"

# ── Backend URL ───────────────────────────────────────────────────────────────
API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _headers() -> dict[str, str]:
    """Build auth headers from the session token."""
    token = session.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


def _remember_user(user: dict) -> None:
    """Keep the authenticated user's profile available to the shared layout."""
    session["user_id"] = user.get("id")
    session["role"] = user.get("role")
    session["user_mobile"] = user.get("mobile")
    session["user_email"] = user.get("email")
    full_name = " ".join(
        part.strip()
        for part in (user.get("first_name"), user.get("last_name"))
        if isinstance(part, str) and part.strip()
    )
    session["user_name"] = full_name or user.get("email") or user.get("mobile") or "User"


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


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get("role") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated


def advertiser_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if session.get("role") != "advertiser":
            abort(403)
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_current_path():
    pending_count = 0
    if session.get("access_token"):
        try:
            _remember_user(_api("GET", "/auth/me"))
        except requests.RequestException:
            # Keep the current display while the API is temporarily unavailable.
            pass
    if session.get("role") == "admin":
        try:
            pending = _api("GET", "/admin/approvals/pending")
            pending_count = sum(len(pending.get(key, [])) for key in ("publishers", "advertisers", "ad_units"))
        except Exception:
            pass
    return {"current_path": flask_request.path, "pending_approval_count": pending_count}

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
                current_user = _api("GET", "/auth/me")
                _remember_user(current_user)
            except Exception:
                session["role"] = None
                session.pop("user_id", None)

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

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "GET":
        return render_template("forgot_password.html", error=None)

    mobile = request.form.get("mobile", "")
    try:
        _api("POST", "/auth/otp/request", json={"mobile": mobile})
    except Exception:
        return render_template("forgot_password.html", error="Could not reach backend. Is it running?")

    session["reset_mobile"] = mobile
    flash("If this number is registered, an OTP has been sent.", "success")
    return redirect(url_for("forgot_password_reset"))

@app.route("/forgot-password/reset", methods=["GET", "POST"])
def forgot_password_reset():
    if "reset_mobile" not in session:
        return redirect(url_for("forgot_password"))

    if request.method == "GET":
        return render_template("forgot_password_reset.html", error=None)

    mobile = session["reset_mobile"]
    code = request.form.get("code", "")
    password = request.form.get("password", "")
    try:
        _api("POST", "/auth/forgot-password/reset", json={"mobile": mobile, "code": code, "password": password})
        session.pop("reset_mobile", None)
        flash("Password reset successfully. Please log in.", "success")
        return redirect(url_for("login"))
    except requests.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", "Failed to reset password")
            if isinstance(detail, list):
                detail = detail[0].get("msg", "Invalid input").replace("Value error, ", "")
        except Exception:
            detail = "Failed to reset password"
        return render_template("forgot_password_reset.html", error=detail)
    except Exception:
        return render_template("forgot_password_reset.html", error="Could not reach backend")

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
    return render_template("campaigns.html", campaigns=campaigns_list, manage_mode=False)


@app.route("/manage-campaign")
@admin_required
def manage_campaigns():
    try:
        campaigns_list = _api("GET", "/campaigns")
    except Exception as exc:
        campaigns_list = []
        flash(f"Could not load campaigns: {exc}", "error")
    return render_template("campaigns.html", campaigns=campaigns_list, manage_mode=True)


@app.route("/campaigns/create", methods=["POST"])
@app.route("/manage-campaign/create", methods=["POST"])
@login_required
def create_campaign():
    if request.path.startswith("/manage-") and session.get("role") != "admin":
        abort(403)
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
    return redirect(url_for("manage_campaigns" if request.path.startswith("/manage-") else "campaigns"))


@app.route("/campaigns/<int:campaign_id>/toggle", methods=["POST"])
@app.route("/manage-campaign/<int:campaign_id>/toggle", methods=["POST"])
@login_required
def toggle_campaign(campaign_id: int):
    if request.path.startswith("/manage-") and session.get("role") != "admin":
        abort(403)
    is_active = request.form.get("is_active") == "true"
    try:
        _api("PATCH", f"/campaigns/{campaign_id}", json={"is_active": is_active})
    except Exception as exc:
        flash(f"Update failed: {exc}", "error")
    return redirect(url_for("manage_campaigns" if request.path.startswith("/manage-") else "campaigns"))

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
@app.route("/manage-campaign/<int:campaign_id>/delete", methods=["POST"])
@login_required
def delete_campaign(campaign_id: int):
    if request.path.startswith("/manage-") and session.get("role") != "admin":
        abort(403)
    try:
        _api("DELETE", f"/campaigns/{campaign_id}")
        flash("Campaign deleted.", "success")
    except Exception as exc:
        flash(f"Delete failed: {exc}", "error")
    return redirect(url_for("manage_campaigns" if request.path.startswith("/manage-") else "campaigns"))


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


@app.route("/manage-advertiser")
@admin_required
def manage_advertisers():
    try:
        advertisers_list = _api("GET", "/admin/advertisers")
    except Exception as exc:
        advertisers_list = []
        flash(f"Could not load advertisers: {exc}", "error")
    return render_template("manage_advertisers.html", advertisers=advertisers_list)


@app.route("/manage-publisher")
@admin_required
def manage_publishers():
    try:
        publishers_list = _api("GET", "/publishers")
    except Exception as exc:
        publishers_list = []
        flash(f"Could not load publishers: {exc}", "error")
    return render_template("manage_publishers.html", publishers=publishers_list)


@app.route("/manage-users")
@admin_required
def manage_users():
    try:
        current_user = _api("GET", "/auth/me")
        _remember_user(current_user)
        users = _api("GET", "/admin/users")
        publishers_list = _api("GET", "/publishers")
        advertisers_list = _api("GET", "/admin/advertisers")
    except Exception as exc:
        users, publishers_list, advertisers_list = [], [], []
        flash(f"Could not load users: {exc}", "error")
    return render_template(
        "manage_users.html",
        users=users,
        publishers=publishers_list,
        advertisers=advertisers_list,
    )


@app.route("/manage-users/<int:user_id>", methods=["POST"])
@admin_required
def update_managed_user(user_id: int):
    role = request.form.get("role", "")
    if role not in {"admin", "staff", "publisher", "advertiser"}:
        flash("Choose a valid user role.", "error")
        return redirect(url_for("manage_users"))

    try:
        payload = {
            "role": role,
            "is_active": request.form.get("is_active") == "true",
            "publisher_id": int(request.form["publisher_id"]) if role == "publisher" and request.form.get("publisher_id") else None,
            "advertiser_id": int(request.form["advertiser_id"]) if role == "advertiser" and request.form.get("advertiser_id") else None,
        }
        _api("PATCH", f"/admin/users/{user_id}", json=payload)
        flash("User updated.", "success")
    except Exception as exc:
        flash(f"Could not update user: {exc}", "error")
    return redirect(url_for("manage_users"))


@app.route("/manage/<kind>/<int:item_id>/status", methods=["POST"])
@admin_required
def manage_entity_status(kind: str, item_id: int):
    if kind not in {"advertisers", "publishers"}:
        abort(404)
    status_value = request.form.get("status", "")
    valid_statuses = {"active", "suspended", "rejected"}
    reason = request.form.get("rejection_reason", "").strip()
    if status_value not in valid_statuses or (status_value == "rejected" and not reason):
        flash("Choose a valid action and provide a rejection reason when rejecting.", "error")
        return redirect(url_for("manage_advertisers" if kind == "advertisers" else "manage_publishers"))
    payload = {"status": status_value}
    if reason:
        payload["rejection_reason"] = reason
    try:
        _api("PATCH", f"/admin/{kind}/{item_id}/review", json=payload)
        flash(f"{kind[:-1].title()} status updated.", "success")
    except Exception as exc:
        flash(f"Could not update {kind[:-1]}: {exc}", "error")
    return redirect(url_for("manage_advertisers" if kind == "advertisers" else "manage_publishers"))


@app.route("/manage-slots")
@admin_required
def manage_slots():
    try:
        publishers_list = _api("GET", "/publishers")
        slots = []
        for publisher in publishers_list:
            for unit in _api("GET", f"/publishers/{publisher['id']}/ad-units"):
                slots.append({**unit, "publisher_name": publisher["name"]})
    except Exception as exc:
        slots = []
        flash(f"Could not load ad slots: {exc}", "error")
    return render_template("manage_slots.html", slots=slots)


@app.route("/manage-slots/<int:slot_id>/review", methods=["POST"])
@admin_required
def manage_slot_review(slot_id: int):
    decision = request.form.get("decision")
    reason = request.form.get("rejection_reason", "").strip()
    if decision not in {"approve", "reject"} or (decision == "reject" and not reason):
        flash("Choose an action and provide a reason when rejecting.", "error")
        return redirect(url_for("manage_slots"))
    payload = {"status": "approved" if decision == "approve" else "rejected"}
    if reason:
        payload["rejection_reason"] = reason
    try:
        _api("PATCH", f"/admin/ad-units/{slot_id}/review", json=payload)
        flash(f"Ad slot {decision}d.", "success")
    except Exception as exc:
        flash(f"Could not update ad slot: {exc}", "error")
    return redirect(url_for("manage_slots"))


@app.route("/manage-slots/<int:slot_id>/active", methods=["POST"])
@admin_required
def manage_slot_active(slot_id: int):
    is_active = request.form.get("is_active") == "true"
    try:
        _api("PATCH", f"/admin/ad-units/{slot_id}/active", json={"is_active": is_active})
        flash("Ad slot status updated.", "success")
    except Exception as exc:
        flash(f"Could not update ad slot: {exc}", "error")
    return redirect(url_for("manage_slots"))


def render_wallet(order=None, checkout_error=None):
    try:
        wallet = _api("GET", "/payments/wallet")
    except Exception as exc:
        wallet = {"balance": 0, "credit_limit": 0, "currency": "INR"}
        if checkout_error is None:
            checkout_error = f"Could not load wallet: {exc}"
    return render_template(
        "advertiser_wallet.html",
        wallet=wallet,
        checkout_order=order,
        checkout_error=checkout_error,
    )


@app.route("/wallet")
@advertiser_required
def advertiser_wallet():
    return render_wallet()


@app.route("/wallet/order", methods=["POST"])
@advertiser_required
def advertiser_wallet_order():
    try:
        order = _api("POST", "/payments/orders", json={"amount": request.form.get("amount", "")})
        return render_wallet(order=order)
    except Exception as exc:
        return render_wallet(checkout_error=f"Could not start payment: {exc}"), 400


@app.route("/wallet/verify", methods=["POST"])
@advertiser_required
def advertiser_wallet_verify():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"detail": "Invalid payment confirmation"}), 400
    try:
        return jsonify(_api("POST", "/payments/verify", json=payload))
    except requests.HTTPError as exc:
        try:
            detail = exc.response.json().get("detail", "Payment confirmation failed")
        except Exception:
            detail = "Payment confirmation failed"
        return jsonify({"detail": detail}), exc.response.status_code
    except Exception:
        return jsonify({"detail": "Could not confirm payment with Razorpay"}), 502


@app.route("/approvals")
@admin_required
def approvals():
    tab = request.args.get("tab", "publishers")
    if tab not in {"publishers", "advertisers", "ad_units"}:
        tab = "publishers"
    try:
        items = _api("GET", "/admin/approvals/pending")
    except Exception as exc:
        items = {"publishers": [], "advertisers": [], "ad_units": []}
        flash(f"Could not load pending approvals: {exc}", "error")
    return render_template("approvals.html", approvals=items, tab=tab)


@app.route("/payments")
@admin_required
def payments():
    payment_status = request.args.get("status", "all")
    allowed_statuses = {"all", "pending", "processing", "paid", "failed", "cancelled"}
    if payment_status not in allowed_statuses:
        payment_status = "all"
    path = "/payouts" if payment_status == "all" else f"/payouts?status={quote(payment_status)}"
    try:
        items = _api("GET", path)
    except Exception as exc:
        items = []
        flash(f"Could not load payments: {exc}", "error")
    return render_template("payments.html", payments=items, payment_status=payment_status)


@app.route("/payments/<int:payment_id>/status", methods=["POST"])
@admin_required
def update_payment_status(payment_id: int):
    new_status = request.form.get("status", "")
    if new_status not in {"pending", "processing", "paid", "cancelled"}:
        flash("Choose a valid payment status.", "error")
        return redirect(url_for("payments"))
    try:
        _api("PATCH", f"/payouts/{payment_id}", json={"status": new_status})
        label = "approved" if new_status == "paid" else new_status
        flash(f"Payment #{payment_id} marked {label}.", "success")
    except Exception as exc:
        flash(f"Could not update payment: {exc}", "error")
    return redirect(url_for("payments", status=request.form.get("filter", "all")))


@app.route("/approvals/<kind>/<int:item_id>/review", methods=["POST"])
@admin_required
def review_approval(kind: str, item_id: int):
    endpoints = {"publishers": "publishers", "advertisers": "advertisers", "ad_units": "ad-units"}
    if kind not in endpoints:
        abort(404)
    decision = request.form.get("decision")
    status_value = "approved" if decision == "approve" and kind == "ad_units" else "active" if decision == "approve" else "rejected"
    reason = request.form.get("rejection_reason", "").strip()
    if decision not in {"approve", "reject"} or (decision == "reject" and not reason):
        flash("Choose an action and provide a reason when rejecting.", "error")
        return redirect(url_for("approvals", tab=kind))
    payload = {"status": status_value}
    if decision == "reject":
        payload["rejection_reason"] = reason
    try:
        _api("PATCH", f"/admin/{endpoints[kind]}/{item_id}/review", json=payload)
        flash(f"{kind.replace('_', ' ').title()} {decision}d.", "success")
    except Exception as exc:
        flash(f"Review failed: {exc}", "error")
    return redirect(url_for("approvals", tab=kind))


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

# ── Live events (for admin) ─────────────────────────────────────────────────

@app.route("/live-events")
@admin_required
def live_events():
    return render_template("live_events.html")


@app.route("/proxy/live-events")
@admin_required
def proxy_live_events():
    params = {"limit": min(request.args.get("limit", 100, type=int), 500)}
    after_id = request.args.get("after_id", type=int)
    if after_id is not None:
        params["after_id"] = after_id
    try:
        return jsonify(_api("GET", "/admin/events/recent", params=params))
    except Exception:
        return jsonify({"detail": "Could not load events"}), 502

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
