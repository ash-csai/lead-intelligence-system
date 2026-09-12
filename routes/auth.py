"""Authentication routes for Flask-Login."""

from flask import Blueprint, render_template, request, redirect, url_for, abort
from flask_login import login_user, logout_user, login_required, current_user
from database.models import User, db
from utils.permissions import require_admin, ADMIN, MANAGER, COUNSELLOR

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Show the login form and authenticate a valid user."""
    error = None

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""

        user = db.session.query(User).filter(User.email == email).first()
        if user and user.check_password(password) and user.is_active:
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


@auth_bp.route("/team", methods=["GET", "POST"])
@login_required
def team():
    """Admin-only team management page for listing and creating users in the same organization."""
    require_admin(current_user)

    db_session = db.session
    organization_id = current_user.organization_id
    roles = [ADMIN, MANAGER, COUNSELLOR]
    error = None
    success = None

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        role = (request.form.get("role") or "Admin").strip()

        if not name or not email or not password:
            error = "Name, email, password, and role are required."
        elif role not in roles:
            error = "Invalid role selected."
        elif db_session.query(User).filter(User.email == email, User.organization_id == organization_id).first():
            error = "A user with that email already exists in this organization."
        else:
            user = User(name=name, email=email, role=role, organization_id=organization_id, is_active=True)
            user.set_password(password)
            db_session.add(user)
            db_session.commit()
            success = f"Created {name} ({email})."
            return redirect("/team")

    users = db_session.query(User).filter(User.organization_id == organization_id).order_by(User.name).all()
    return render_template("team.html", users=users, roles=roles, error=error, success=success)


@auth_bp.route("/team/<int:user_id>", methods=["POST"])
@login_required
def update_team_user(user_id):
    """Update an organization user’s role and active state from the admin-only management page."""
    require_admin(current_user)

    organization_id = current_user.organization_id
    user = db.session.query(User).filter(User.user_id == user_id, User.organization_id == organization_id).first()
    if user is None:
        abort(404)

    role = (request.form.get("role") or user.role).strip()
    if role not in {ADMIN, MANAGER, COUNSELLOR}:
        abort(400)

    user.role = role
    user.is_active = request.form.get("is_active") == "on"
    db.session.commit()

    return redirect("/team")
