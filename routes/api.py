"""Versioned bearer-token API routes for the Lead Intelligence System.

The browser UI remains session-based through Flask-Login. The API is kept
separate and uses a hashed token record in the database so a client can use an
HTTP Bearer token without needing a browser cookie.
"""

import hashlib
import secrets
from datetime import datetime

from flask import jsonify, request, g
from flask_login import login_required, current_user
from flask_smorest import Blueprint as SmorestBlueprint
from sqlalchemy.exc import OperationalError

from database.models import db, User, Lead, Interaction, ApiToken
from utils.permissions import COUNSELLOR


api_bp = SmorestBlueprint("api_v1", "routes.api", url_prefix="/api/v1", description="Versioned token-authenticated API")


@api_bp.before_request
def _api_auth_guard():
    """Authenticate API requests using Authorization: Bearer <token>."""
    path = request.path
    if path == "/api/v1/token" or path.startswith("/api/v1/docs"):
        return None

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    raw_token = header.split(" ", 1)[1].strip()
    if not raw_token:
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    try:
        token_record = db.session.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
    except (OperationalError, RuntimeError):
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    if token_record is None:
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    user = db.session.query(User).filter(User.user_id == token_record.user_id).first()
    if user is None or not user.is_active:
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    g.api_user = user
    return None


@api_bp.route("/token", methods=["GET", "POST"])
@login_required
def manage_token():
    """Issue or inspect a bearer token for the logged-in web session user."""
    if request.method == "POST":
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        existing = db.session.query(ApiToken).filter(ApiToken.user_id == current_user.user_id).first()
        if existing:
            existing.token_hash = token_hash
            existing.created_at = datetime.utcnow()
        else:
            db.session.add(ApiToken(user_id=current_user.user_id, token_hash=token_hash))

        db.session.commit()
        return jsonify({"token": raw_token, "token_type": "bearer"}), 201

    return jsonify({"message": "POST /api/v1/token to create a bearer token for the current logged-in user."})


@api_bp.route("/leads", methods=["GET"])
def list_leads():
    """Return org-wide or counsellor-owned leads, matching the web UI’s role scope."""
    user = g.get("api_user")
    if user is None:
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    query = db.session.query(Lead).filter(Lead.organization_id == user.organization_id)
    if user.role == COUNSELLOR:
        query = query.filter(Lead.assigned_to == user.user_id)

    leads = query.order_by(Lead.lead_id.desc()).all()
    payload = [{
        "lead_id": lead.lead_id,
        "student_name": lead.student_name,
        "status": lead.status,
        "assigned_to": lead.assigned_to,
        "organization_id": lead.organization_id,
    } for lead in leads]
    return jsonify(payload)


@api_bp.route("/leads/<int:lead_id>", methods=["GET"])
def get_lead(lead_id):
    """Read an individual lead using the same organization and ownership scope as the browser UI."""
    user = g.get("api_user")
    if user is None:
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        return jsonify({"error": "Not found"}), 404

    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        return jsonify({"error": "Forbidden"}), 403

    return jsonify({
        "lead_id": lead.lead_id,
        "student_name": lead.student_name,
        "status": lead.status,
        "assigned_to": lead.assigned_to,
        "organization_id": lead.organization_id,
    })


@api_bp.route("/interactions", methods=["GET"])
def list_interactions():
    """Return interactions visible to the token holder within the same organization scope."""
    user = g.get("api_user")
    if user is None:
        return jsonify({"error": "Missing or invalid bearer token."}), 401

    # Keep the API separate from the UI session; scope by organization and, for counsellors, ownership through assigned leads.
    query = db.session.query(Interaction).join(Lead, Interaction.lead_id == Lead.lead_id)
    query = query.filter(Lead.organization_id == user.organization_id)
    if user.role == COUNSELLOR:
        query = query.filter(Lead.assigned_to == user.user_id)

    interactions = query.order_by(Interaction.interaction_id.desc()).all()
    payload = [{
        "interaction_id": interaction.interaction_id,
        "lead_id": interaction.lead_id,
        "interaction_type": interaction.interaction_type,
        "notes": interaction.notes,
    } for interaction in interactions]
    return jsonify(payload)
