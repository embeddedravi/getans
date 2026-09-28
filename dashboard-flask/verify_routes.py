"""Mobile verification pages for the Flask dashboard.

Register in app.py (after `app = Flask(...)`):

    from verify_routes import verify_bp
    app.register_blueprint(verify_bp)
"""

from __future__ import annotations

import os

import requests
from flask import Blueprint, flash, redirect, render_template, request, url_for

verify_bp = Blueprint("verify", __name__)

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000/api")


def _post(path: str, payload: dict) -> requests.Response:
    return requests.post(f"{API_BASE}{path}", json=payload, timeout=10)


def _error_from(resp: requests.Response) -> str:
    """Turn a FastAPI error body (string or 422 list) into a message."""
    try:
        detail = resp.json().get("detail")
    except ValueError:
        detail = None
    if isinstance(detail, list):
        return ", ".join(
            str(d.get("msg", "Invalid input")).replace("Value error, ", "") for d in detail
        )
    if isinstance(detail, str):
        return detail
    return "Something went wrong. Try again."


@verify_bp.route("/verify", methods=["GET", "POST"])
def verify_page():
    if request.method == "GET":
        return render_template("verify.html", step="mobile")

    action = request.form.get("action")
    mobile = request.form.get("mobile", "").strip()

    try:
        if action == "request":
            resp = _post("/auth/otp/request", {"mobile": mobile})
            if resp.ok:
                data = resp.json()
                return render_template(
                    "verify.html",
                    step="code",
                    mobile=mobile,
                    resend_after=data.get("resend_after", 60),
                )
            # Can't send: stay on the step the person was on.
            step = "code" if request.form.get("resend") else "mobile"
            return render_template(
                "verify.html", step=step, mobile=mobile, error=_error_from(resp), resend_after=0
            )

        if action == "verify":
            code = request.form.get("code", "").strip()
            resp = _post("/auth/otp/verify", {"mobile": mobile, "code": code})
            if resp.ok:
                flash("Mobile number verified. You can sign in now.", "success")
                return redirect(url_for("login"))
            return render_template(
                "verify.html", step="code", mobile=mobile, error=_error_from(resp), resend_after=0
            )
    except requests.RequestException:
        return render_template(
            "verify.html",
            step="code" if action == "verify" else "mobile",
            mobile=mobile,
            error="Could not reach the backend. Is it running?",
            resend_after=0,
        )

    return redirect(url_for("verify.verify_page"))
