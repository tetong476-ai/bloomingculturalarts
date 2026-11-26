import json
import os
import secrets
import time
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from database import db, SiteSetting, User
from functools import wraps

auth_bp = Blueprint("auth", __name__)
PASSWORD_RESET_TTL = 600


def _settings():
    return {setting.key: setting.value for setting in SiteSetting.query.all()}


def _normalize_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = "855" + digits[1:]
    return digits


def _send_vonage_code(phone, code):
    api_key = os.getenv("VONAGE_API_KEY")
    api_secret = os.getenv("VONAGE_API_SECRET")
    brand_name = os.getenv("VONAGE_BRAND_NAME", "BCA")
    if not api_key or not api_secret:
        raise RuntimeError("Vonage SMS is not configured. Set VONAGE_API_KEY and VONAGE_API_SECRET.")

    payload = urlencode({
        "api_key": api_key,
        "api_secret": api_secret,
        "from": brand_name,
        "to": phone,
        "text": f"Your BCA password reset code is {code}. It expires in 10 minutes.",
    }).encode()
    request = Request("https://rest.nexmo.com/sms/json", data=payload, method="POST")
    with urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode())
    message = result.get("messages", [{}])[0]
    if message.get("status") != "0":
        raise RuntimeError(message.get("error-text", "Vonage rejected the SMS request."))


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(next_page or url_for("admin.dashboard"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html")


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        configured_phone = _settings().get("phone", "").strip()
        if not phone or _normalize_phone(phone) != _normalize_phone(configured_phone):
            flash("The phone number does not match the admin account.", "error")
            return render_template("forgot_password.html", step="phone", phone=phone)

        phone = _normalize_phone(configured_phone)
        code = f"{secrets.randbelow(1_000_000):06d}"
        try:
            _send_vonage_code(phone, code)
        except (RuntimeError, OSError, json.JSONDecodeError) as error:
            flash(str(error), "error")
            return render_template("forgot_password.html", step="phone", phone=phone)

        session["password_reset"] = {
            "otp_hash": generate_password_hash(code),
            "expires_at": time.time() + PASSWORD_RESET_TTL,
            "verified": False,
        }
        return redirect(url_for("auth.forgot_password_verify"))

    return render_template("forgot_password.html", step="phone")


@auth_bp.route("/forgot-password/verify", methods=["GET", "POST"])
def forgot_password_verify():
    reset = session.get("password_reset")
    if not reset or reset.get("expires_at", 0) < time.time():
        session.pop("password_reset", None)
        flash("Your reset code has expired. Please request a new one.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if not check_password_hash(reset["otp_hash"], code):
            flash("The verification code is incorrect.", "error")
            return render_template("forgot_password.html", step="verify")
        reset["verified"] = True
        session["password_reset"] = reset
        return redirect(url_for("auth.forgot_password_reset"))

    return render_template("forgot_password.html", step="verify")


@auth_bp.route("/forgot-password/reset", methods=["GET", "POST"])
def forgot_password_reset():
    reset = session.get("password_reset")
    if not reset or not reset.get("verified") or reset.get("expires_at", 0) < time.time():
        session.pop("password_reset", None)
        flash("Please verify a new reset code first.", "error")
        return redirect(url_for("auth.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            user = User.query.filter_by(role="admin").first()
            if not user:
                flash("Admin account could not be found.", "error")
            else:
                user.set_password(password)
                db.session.commit()
                session.pop("password_reset", None)
                return render_template("forgot_password.html", step="success")

    return render_template("forgot_password.html", step="reset")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
