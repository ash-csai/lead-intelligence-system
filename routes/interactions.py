import sqlite3
from flask import Blueprint, request, redirect, abort
from database.db_connection import get_db
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input

interactions_bp = Blueprint('interactions', __name__)


@interactions_bp.route('/leads/update_status/<int:lead_id>', methods=['POST'])
def update_status(lead_id):
    db = get_db()

    new_status = request.form["status"]

    cursor = db.execute("""
        UPDATE leads
        SET status = ?
        WHERE lead_id = ?
    """, (new_status, lead_id))

    if cursor.rowcount == 0:
        abort(404)

    recalculate_and_persist_score(db, lead_id)
    db.commit()

    return redirect(f"/leads/{lead_id}")


@interactions_bp.route('/interactions/add/<int:lead_id>', methods=['POST'])
def auto_add_interaction(lead_id):
    db = get_db()

    interaction_type = request.form["interaction_type"]
    notes = request.form["notes"]
    follow_up_date = normalize_form_input("follow_up_date", request.form["follow_up_date"])

    try:
        db.execute("""
            INSERT INTO interactions
            (lead_id, interaction_type, notes, follow_up_date)
            VALUES (?, ?, ?, ?)
        """, (lead_id, interaction_type, notes, follow_up_date))
    except sqlite3.IntegrityError:
        abort(404)

    # Smart Status Suggestion Logic
    if interaction_type == "call":
        db.execute("UPDATE leads SET status='contacted' WHERE lead_id=?", (lead_id,))
    elif interaction_type == "visit":
        db.execute("UPDATE leads SET status='interested' WHERE lead_id=?", (lead_id,))
    elif interaction_type == "application":
        db.execute("UPDATE leads SET status='applied' WHERE lead_id=?", (lead_id,))

    recalculate_and_persist_score(db, lead_id)
    db.commit()

    return redirect(f"/leads/{lead_id}")


@interactions_bp.route('/quick_action/<int:lead_id>', methods=['POST'])
def quick_action(lead_id):
    db = get_db()

    action_type = request.form["action_type"]

    # Store as interaction
    db.execute("""
        INSERT INTO interactions (lead_id, interaction_type, notes)
        VALUES (?, ?, ?)
    """, (lead_id, action_type, "Quick action performed"))

    recalculate_and_persist_score(db, lead_id)
    db.commit()

    return redirect("/")
