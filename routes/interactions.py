"""Interactions routes using SQLAlchemy ORM."""

from flask import Blueprint, request, redirect, abort
from database.db_connection import get_db
from database.models import Lead, Interaction
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input
from sqlalchemy.exc import IntegrityError
from datetime import datetime

interactions_bp = Blueprint('interactions', __name__)


@interactions_bp.route('/leads/update_status/<int:lead_id>', methods=['POST'])
def update_status(lead_id):
    db = get_db()

    new_status = request.form.get("status")

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
    if lead is None:
        abort(404)

    lead.status = new_status

    try:
        db.session.flush()
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400) # Bad status or constraint violation

    return redirect(f"/leads/{lead_id}")


@interactions_bp.route('/interactions/add/<int:lead_id>', methods=['POST'])
def auto_add_interaction(lead_id):
    db = get_db()

    interaction_type = request.form.get("interaction_type")
    notes = request.form.get("notes")
    follow_up_date_str = normalize_form_input("follow_up_date", request.form.get("follow_up_date", ""))

    follow_up_date = None
    if follow_up_date_str:
        try:
            follow_up_date = datetime.strptime(follow_up_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Check if lead exists first (to raise 404 if not found)
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
    if lead is None:
        abort(404)

    # Create new interaction
    interaction = Interaction(
        lead_id=lead_id,
        interaction_type=interaction_type,
        notes=notes,
        follow_up_date=follow_up_date
    )
    db.session.add(interaction)

    # Smart Status Suggestion Logic
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
def quick_action(lead_id):
    db = get_db()

    action_type = request.form.get("action_type")

    # Check if lead exists first
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
    if lead is None:
        abort(404)

    # Store as interaction
    interaction = Interaction(
        lead_id=lead_id,
        interaction_type=action_type,
        notes="Quick action performed"
    )
    db.session.add(interaction)

    try:
        db.session.flush()
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(404)

    return redirect("/")
