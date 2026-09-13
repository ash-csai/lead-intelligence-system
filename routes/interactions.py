"""Interactions routes using SQLAlchemy ORM."""

from flask import Blueprint, request, redirect, abort
from flask_login import login_required, current_user
from database.db_connection import get_db
from database.models import Lead, Interaction
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input
from utils.permissions import require_lead_access, COUNSELLOR
from sqlalchemy.exc import IntegrityError
from datetime import datetime

interactions_bp = Blueprint('interactions', __name__)


@interactions_bp.route('/leads/update_status/<int:lead_id>', methods=['POST'])
@login_required
def update_status(lead_id):
    db = get_db()
    organization_id = current_user.organization_id

    new_status = request.form.get("status")

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == organization_id).first()
    if lead is None:
        abort(404)
    if current_user.role == COUNSELLOR and lead.assigned_to != current_user.user_id:
        abort(403)

    lead.status = new_status

    try:
        db.session.flush()
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400)

    return redirect(f"/leads/{lead_id}")


@interactions_bp.route('/interactions/add/<int:lead_id>', methods=['POST'])
@login_required
def auto_add_interaction(lead_id):
    db = get_db()
    organization_id = current_user.organization_id

    interaction_type = request.form.get("interaction_type")
    notes = request.form.get("notes")
    follow_up_date_str = normalize_form_input("follow_up_date", request.form.get("follow_up_date", ""))

    follow_up_date = None
    if follow_up_date_str:
        try:
            follow_up_date = datetime.strptime(follow_up_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == organization_id).first()
    if lead is None:
        abort(404)
    if current_user.role == COUNSELLOR and lead.assigned_to != current_user.user_id:
        abort(403)

    interaction = Interaction(
        lead_id=lead_id,
        interaction_type=interaction_type,
        notes=notes,
        follow_up_date=follow_up_date,
        organization_id=organization_id,
    )
    db.session.add(interaction)

    if interaction_type == "call":
        lead.status = 'contacted'
    elif interaction_type == "visit":
        lead.status = 'interested'
    elif interaction_type == "application":
        lead.status = 'applied'

    try:
        db.session.flush()
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(404)

    return redirect(f"/leads/{lead_id}")


@interactions_bp.route('/quick_action/<int:lead_id>', methods=['POST'])
@login_required
def quick_action(lead_id):
    db = get_db()
    organization_id = current_user.organization_id

    action_type = request.form.get("action_type")

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == organization_id).first()
    if lead is None:
        abort(404)
    if current_user.role == COUNSELLOR and lead.assigned_to != current_user.user_id:
        abort(403)

    interaction = Interaction(
        lead_id=lead_id,
        interaction_type=action_type,
        notes="Quick action performed",
        organization_id=organization_id,
    )
    db.session.add(interaction)

    try:
        db.session.flush()
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(404)

    if request.headers.get("HX-Request") == "true":
        return "", 200

    return redirect("/")
