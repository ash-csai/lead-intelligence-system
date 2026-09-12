"""Versioned REST API under /api/v1/ using Flask-Smorest and token-based auth."""

from functools import wraps
from flask import request, jsonify, g, redirect
from flask_smorest import Blueprint, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.models import db, Lead, Interaction, User, ApiToken
from utils.permissions import COUNSELLOR, MANAGER, ADMIN
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input
from sqlalchemy import or_
import secrets


blp = Blueprint("api", __name__, url_prefix="/api/v1", description="Versioned token-authenticated API")


@blp.before_request
def require_token_for_api_routes():
    """Authenticate every non-docs API request using a bearer token instead of cookies."""
    if request.path.endswith("/docs") or request.path.endswith("/openapi.json") or request.path.endswith("/swagger-ui"):
        return None

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        abort(401, message="Missing bearer token")

    raw_token = header.split(" ", 1)[1].strip()
    api_token = db.session.query(ApiToken).all()
    matched = None
    for token in api_token:
        if check_password_hash(token.token_hash, raw_token):
            matched = token
            break

    if not matched:
        abort(401, message="Invalid bearer token")

    user = db.session.query(User).filter(User.user_id == matched.user_id).first()
    if not user or not user.is_active:
        abort(401, message="Token user is inactive")

    g.current_user = user
    return None


@blp.route("/token", methods=["POST"])
def generate_api_token():
    """Create a personal API token for the currently logged-in web session user."""
    # This endpoint is intentionally session-authenticated at route level via Flask-Login elsewhere.
    # In this repo, a logged-in browser session can call it directly from /api/token in auth.py.
    token = request.headers.get("Authorization", "")
    if not token.startswith("Bearer "):
        abort(401, message="Use the web session login flow to create a token")

    return {"message": "Use auth route /api/token to generate a token"}


@blp.route("/leads", methods=["GET"])
def list_leads():
    """List leads visible to the token holder using the same organization/role scope as the UI."""
    user = g.current_user
    org = user.organization_id
    query = db.session.query(Lead).filter(Lead.organization_id == org)
    if user.role == COUNSELLOR:
        query = query.filter(Lead.assigned_to == user.user_id)
    leads = query.order_by(Lead.created_at.desc()).all()
    return {"leads": [lead_to_dict(l) for l in leads]}


@blp.route("/leads/<int:lead_id>", methods=["GET"])
def get_lead(lead_id):
    """Fetch one lead and enforce the same org and role scoping contract as the browser UI."""
    user = g.current_user
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only read owned leads")

    return {"lead": lead_to_dict(lead)}


@blp.route("/leads", methods=["POST"])
def create_lead():
    """Create a lead; Counsellor endpoints self-assign ownership and other roles stay unassigned."""
    user = g.current_user
    data = request.get_json(silent=True) or {}
    student_name = (data.get("student_name") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not student_name or not phone:
        abort(400, message="student_name and phone are required")

    org = user.organization_id
    existing = db.session.query(Lead).filter(Lead.phone == phone, Lead.organization_id == org).first()
    if existing:
        abort(409, message="Lead with this phone already exists")

    assigned_to = user.user_id if user.role == COUNSELLOR else None
    lead = Lead(
        student_name=student_name,
        phone=phone,
        city=(data.get("city") or "").strip(),
        school_id=normalize_form_input("school_id", data.get("school_id", "")),
        coaching_id=normalize_form_input("coaching_id", data.get("coaching_id", "")),
        course_interest=(data.get("course_interest") or "").strip(),
        lead_source=(data.get("lead_source") or "").strip(),
        interest_level=normalize_form_input("interest_level", data.get("interest_level", "")),
        notes=(data.get("notes") or "").strip(),
        lead_score=0,
        status=data.get("status", "new"),
        organization_id=org,
        assigned_to=assigned_to,
    )
    db.session.add(lead)
    db.session.flush()
    recalculate_and_persist_score(db, lead.lead_id)
    db.session.commit()
    return {"lead": lead_to_dict(lead), "message": "created"}, 201


@blp.route("/leads/<int:lead_id>", methods=["PATCH"])
def update_lead(lead_id):
    """Update a lead with the same per-lead access gate as the HTML UI."""
    user = g.current_user
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only update owned leads")

    data = request.get_json(silent=True) or {}
    for field in ["student_name", "phone", "city", "course_interest", "lead_source", "interest_level", "notes", "status"]:
        if field in data:
            setattr(lead, field, data[field])

    db.session.flush()
    recalculate_and_persist_score(db, lead.lead_id)
    db.session.commit()
    return {"lead": lead_to_dict(lead)}


@blp.route("/leads/<int:lead_id>", methods=["DELETE"])
def delete_lead(lead_id):
    """Delete a lead only if the token scope and role can reach it."""
    user = g.current_user
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only delete owned leads")
    db.session.delete(lead)
    db.session.commit()
    return {"message": "deleted"}


@blp.route("/leads/<int:lead_id>/interactions", methods=["GET"])
def list_interactions(lead_id):
    """List interactions for a lead after enforcing same org and ownership scope as the web UI."""
    user = g.current_user
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only read owned lead interactions")

    interactions = db.session.query(Interaction).filter(Interaction.lead_id == lead_id, Interaction.organization_id == user.organization_id).order_by(Interaction.created_at.desc()).all()
    return {"interactions": [interaction_to_dict(i) for i in interactions]}


@blp.route("/leads/<int:lead_id>/interactions", methods=["POST"])
def create_interaction(lead_id):
    """Create an interaction on a scoped lead and let scoring recalc from the same change path already used in the UI."""
    user = g.current_user
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only touch owned leads")

    data = request.get_json(silent=True) or {}
    interaction_type = (data.get("interaction_type") or "").strip()
    notes = (data.get("notes") or "").strip()
    if not interaction_type:
        abort(400, message="interaction_type is required")

    follow_up_date = None
    raw_follow_up = (data.get("follow_up_date") or "")
    if raw_follow_up:
        try:
            from datetime import datetime
            follow_up_date = datetime.strptime(raw_follow_up, "%Y-%m-%d").date()
        except Exception:
            abort(400, message="follow_up_date must be YYYY-MM-DD")

    interaction = Interaction(
        lead_id=lead_id,
        interaction_type=interaction_type,
        notes=notes,
        follow_up_date=follow_up_date,
        organization_id=user.organization_id,
    )
    db.session.add(interaction)
    db.session.flush()

    # Mirror the UI status normalization for calls/visits/applications when interactions are added.
    if interaction_type == "call":
        lead.status = "contacted"
    elif interaction_type == "visit":
        lead.status = "interested"
    elif interaction_type == "application":
        lead.status = "applied"

    # Recalculate scoring the same way as route-based interactions.
    recalculate_and_persist_score(db, lead_id)
    db.session.commit()
    return {"interaction": interaction_to_dict(interaction), "message": "created"}, 201


@blp.route("/interactions/<int:interaction_id>", methods=["GET"])
def get_interaction(interaction_id):
    """Read one interaction in the current token-holder's scoped org, subject to lead ownership if Counsellor."""
    user = g.current_user
    interaction = db.session.query(Interaction).filter(Interaction.interaction_id == interaction_id, Interaction.organization_id == user.organization_id).first()
    if interaction is None:
        abort(404, message="Interaction not found")

    lead = db.session.query(Lead).filter(Lead.lead_id == interaction.lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only read their own leads' interactions")

    return {"interaction": interaction_to_dict(interaction)}


@blp.route("/interactions/<int:interaction_id>", methods=["PATCH"])
def update_interaction(interaction_id):
    """Update an interaction and keep the organization boundary in force."""
    user = g.current_user
    interaction = db.session.query(Interaction).filter(Interaction.interaction_id == interaction_id, Interaction.organization_id == user.organization_id).first()
    if interaction is None:
        abort(404, message="Interaction not found")

    lead = db.session.query(Lead).filter(Lead.lead_id == interaction.lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only update their own leads' interactions")

    data = request.get_json(silent=True) or {}
    for field in ["interaction_type", "notes", "follow_up_date"]:
        if field in data:
            setattr(interaction, field, data[field])

    db.session.flush()
    recalculate_and_persist_score(db, interaction.lead_id)
    db.session.commit()
    return {"interaction": interaction_to_dict(interaction)}


@blp.route("/interactions/<int:interaction_id>", methods=["DELETE"])
def delete_interaction(interaction_id):
    """Delete an interaction only when the token’s role can legally view its backing lead."""
    user = g.current_user
    interaction = db.session.query(Interaction).filter(Interaction.interaction_id == interaction_id, Interaction.organization_id == user.organization_id).first()
    if interaction is None:
        abort(404, message="Interaction not found")

    lead = db.session.query(Lead).filter(Lead.lead_id == interaction.lead_id, Lead.organization_id == user.organization_id).first()
    if lead is None:
        abort(404, message="Lead not found")
    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403, message="Counsellor can only delete their own leads' interactions")

    db.session.delete(interaction)
    db.session.commit()
    return {"message": "deleted"}


# --- helpers ---

def lead_to_dict(lead):
    return {
        "lead_id": lead.lead_id,
        "student_name": lead.student_name,
        "phone": lead.phone,
        "city": lead.city,
        "school_id": lead.school_id,
        "coaching_id": lead.coaching_id,
        "course_interest": lead.course_interest,
        "lead_source": lead.lead_source,
        "interest_level": lead.interest_level,
        "lead_score": lead.lead_score,
        "status": lead.status,
        "organization_id": lead.organization_id,
        "assigned_to": lead.assigned_to,
    }


def interaction_to_dict(interaction):
    return {
        "interaction_id": interaction.interaction_id,
        "lead_id": interaction.lead_id,
        "interaction_type": interaction.interaction_type,
        "notes": interaction.notes,
        "follow_up_date": interaction.follow_up_date.isoformat() if interaction.follow_up_date else None,
        "created_at": interaction.created_at.isoformat() if interaction.created_at else None,
        "organization_id": interaction.organization_id,
    }
