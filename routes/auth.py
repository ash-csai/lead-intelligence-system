"""Authentication routes for Flask-Login."""

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from database.models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form and authenticate a valid user."""
    error = None

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = db.session.query(User).filter(User.email == email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.dashboard"))

        error = "Invalid email or password."

    return render_template("login.html", error=error)


@auth_bp.route("/logout")
@login_required
def logout():
    """Log out the current user and return to the login page."""
    logout_user()
    return redirect(url_for("auth.login"))
