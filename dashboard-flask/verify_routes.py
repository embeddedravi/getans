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


def _captcha_challenge():
    try:
        response = requests.get(f"{API_BASE}/auth/captcha-challenge", timeout=5)
        response.raise_for_status()
        data = response.json()
        # Validate the response has the expected fields
        if isinstance(data, dict) and "challenge" in data and "question" in data:
            return data
        print(f"[verify] CAPTCHA challenge response missing fields: {data}")
        return None
    except requests.RequestException as e:
        print(f"[verify] CAPTCHA challenge request failed: {e}")
        return None
    except ValueError as e:
        print(f"[verify] CAPTCHA challenge JSON parse failed: {e}")
        return None


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
        captcha = _captcha_challenge()
        if captcha is None:
            flash("Unable to load verification challenge. Please ensure the API server is running and try again.", "error")
        return render_template("verify.html", step="mobile", captcha=captcha)

    action = request.form.get("action")
    mobile = request.form.get("mobile", "").strip()

    try:
        if action == "request":
            captcha_challenge = request.form.get("captcha_challenge")
            captcha_answer = request.form.get("captcha_answer")
            
            if not captcha_challenge or not captcha_answer:
                return render_template(
                    "verify.html", step="mobile", mobile=mobile, 
                    error="Please complete the CAPTCHA challenge.", resend_after=0, captcha=_captcha_challenge()
                )
            
            resp = _post("/auth/otp/request", {"mobile": mobile, "captcha_challenge": captcha_challenge, "captcha_answer": captcha_answer})
            if resp.ok:
                data = resp.json()
                return render_template(
                    "verify.html",
                    step="code",
                    mobile=mobile,
                    resend_after=data.get("resend_after", 60),
                    captcha=_captcha_challenge(),
                )
            # Can't send: stay on the step the person was on.
            step = "code" if request.form.get("resend") else "mobile"
            error_msg = _error_from(resp)
            # If CAPTCHA expired/incorrect, provide a fresh one
            new_captcha = _captcha_challenge()
            if "CAPTCHA" in error_msg and new_captcha:
                error_msg += " A new challenge has been loaded below."
            return render_template(
                "verify.html", step=step, mobile=mobile, error=error_msg, resend_after=0, captcha=new_captcha
            )

        if action == "verify":
            code = request.form.get("code", "").strip()
            resp = _post("/auth/otp/verify", {"mobile": mobile, "code": code})
            if resp.ok:
                flash("Mobile number verified. You can sign in now.", "success")
                return redirect(url_for("login"))
            return render_template(
                "verify.html", step="code", mobile=mobile, error=_error_from(resp), resend_after=0, captcha=_captcha_challenge()
            )
    except requests.RequestException as e:
        print(f"[verify] Request failed: {e}")
        return render_template(
            "verify.html",
            step="code" if action == "verify" else "mobile",
            mobile=mobile,
            error="Could not reach the backend. Is it running?",
            resend_after=0,
            captcha=_captcha_challenge(),
        )

    return redirect(url_for("verify.verify_page"))
