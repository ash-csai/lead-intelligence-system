"""Leads routes using SQLAlchemy ORM."""

from flask import Blueprint, render_template, request, redirect, abort, url_for
from flask_login import login_required, current_user
from database.db_connection import get_db
from database.models import Lead, Institution, Interaction, User
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input
from utils.permissions import require_lead_access, user_can_access_lead, COUNSELLOR, MANAGER, ADMIN
from sqlalchemy import or_
from datetime import date

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/leads')
@login_required
def lead_list():
    """List all leads with optional filtering by query, city, status, course."""
    db = get_db()
    organization_id = current_user.organization_id

    query = request.args.get("q")
    city = request.args.get("city")
    status = request.args.get("status")
    course = request.args.get("course")

    # Start with base query
    leads_query = db.session.query(Lead).filter(Lead.organization_id == organization_id)
    if current_user.role == COUNSELLOR:
        leads_query = leads_query.filter(Lead.assigned_to == current_user.user_id)
    leads_query = leads_query.order_by(Lead.created_at.desc())

    # Apply filters
    if query:
        search_term = f"%{query}%"
        leads_query = leads_query.filter(or_(Lead.student_name.ilike(search_term), Lead.phone.ilike(search_term)))
    if city:
        leads_query = leads_query.filter(Lead.city == city)
    if status:
        leads_query = leads_query.filter(Lead.status == status)
    if course:
        leads_query = leads_query.filter(Lead.course_interest == course)

    leads = leads_query.all()

    counsellors = []
    if current_user.role in {ADMIN, MANAGER}:
        counsellors = (
            db.session.query(User)
            .filter(User.organization_id == organization_id, User.role == COUNSELLOR)
            .order_by(User.name.asc())
            .all()
        )

    status_options = ["new", "contacted", "interested", "applied", "admitted", "lost"]

    if request.headers.get("HX-Request") == "true":
        return render_template("leads_table_fragment.html", leads=leads, counsellors=counsellors, status_options=status_options)

    return render_template("leads.html", leads=leads, counsellors=counsellors, status_options=status_options)


@leads_bp.route('/leads/bulk_action', methods=['POST'])
@login_required
def bulk_action():
    """Apply a role-scoped bulk lead reassign or status update using the same scoring flow as single-item updates."""
    db = get_db()
    organization_id = current_user.organization_id
    action = request.form.get("bulk_action")
    selected_ids = request.form.getlist("lead_id")

    if not selected_ids:
        return redirect("/leads")

    try:
        parsed_ids = [int(lead_id) for lead_id in selected_ids]
    except (TypeError, ValueError):
        abort(400)

    leads_query = db.session.query(Lead).filter(Lead.organization_id == organization_id, Lead.lead_id.in_(parsed_ids))
    if current_user.role == COUNSELLOR:
        leads_query = leads_query.filter(Lead.assigned_to == current_user.user_id)

    leads = leads_query.all()
    if not leads:
        return redirect("/leads")

    if action == "reassign":
        if current_user.role not in {ADMIN, MANAGER}:
            abort(403)

        target_user_id = request.form.get("counsellor_id")
        try:
            target_user_id = int(target_user_id)
        except (TypeError, ValueError):
            abort(400)

        target = (
            db.session.query(User)
            .filter(User.user_id == target_user_id, User.organization_id == organization_id, User.role == COUNSELLOR)
            .first()
        )
        if target is None:
            abort(400)

        for lead in leads:
            lead.assigned_to = target.user_id

        db.session.commit()
        return redirect("/leads")

    if action == "status":
        new_status = (request.form.get("bulk_status") or "").strip()
        allowed_statuses = {"new", "contacted", "interested", "applied", "admitted", "lost"}
        if new_status not in allowed_statuses:
            abort(400)

        # Counsellor can update only their own org-scoped leads; Manager/Admin can update the same org-wide queue.
        for lead in leads:
            lead.status = new_status
            db.session.flush()
            recalculate_and_persist_score(db, lead.lead_id)

        db.session.commit()
        if request.headers.get("HX-Request") == "true":
            leads_query = db.session.query(Lead).filter(Lead.organization_id == organization_id)
            if current_user.role == COUNSELLOR:
                leads_query = leads_query.filter(Lead.assigned_to == current_user.user_id)
            leads = leads_query.order_by(Lead.created_at.desc()).all()

            counsellors = []
            if current_user.role in {ADMIN, MANAGER}:
                counsellors = (
                    db.session.query(User)
                    .filter(User.organization_id == organization_id, User.role == COUNSELLOR)
                    .order_by(User.name.asc())
                    .all()
                )

            status_options = ["new", "contacted", "interested", "applied", "admitted", "lost"]
            return render_template("leads_table_fragment.html", leads=leads, counsellors=counsellors, status_options=status_options)

        return redirect("/leads")

    abort(400)


@leads_bp.route('/leads/<int:lead_id>')
@login_required
def lead_detail(lead_id):
    """Show details for a specific lead and its interactions."""
    db = get_db()
    organization_id = current_user.organization_id

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == organization_id).first()
    if lead is None:
        abort(404)

    # Counsellor must only see their own assigned lead.
    if current_user.role == COUNSELLOR and lead.assigned_to != current_user.user_id:
        abort(403)

    # Interactions are eager-loaded via the relationship
    interactions = lead.interactions

    return render_template("lead_detail.html", lead=lead, interactions=interactions)


@leads_bp.route('/leads/add', methods=['GET', 'POST'])
@login_required
def add_lead():
    """Add a new lead for any role in the organization."""
    db = get_db()
    organization_id = current_user.organization_id

    # Counsellors, Managers, and Admins may all open the add-lead form and submit a new lead.
    # Ownership assignment is role-dependent: counsellors self-assign, while admin/manager
    # submissions stay unassigned unless a future UI explicitly lets them pick an assignee.
    schools = db.session.query(Institution).filter(Institution.type == 'school', Institution.organization_id == organization_id).all()
    coachings = db.session.query(Institution).filter(Institution.type == 'coaching_center', Institution.organization_id == organization_id).all()

    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        phone = request.form.get("phone", "").strip()

        if not student_name:
            return "Student name is required"
        if not phone:
            return "Phone number is required"

        existing = db.session.query(Lead).filter(Lead.phone == phone, Lead.organization_id == organization_id).first()
        if existing:
            return "Lead with this phone already exists"

        city = request.form.get("city", "").strip()
        school_id = normalize_form_input("school_id", request.form.get("school_id", ""))
        coaching_id = normalize_form_input("coaching_id", request.form.get("coaching_id", ""))
        course_interest = request.form.get("course_interest", "").strip()
        lead_source = request.form.get("lead_source", "").strip()
        interest_level = normalize_form_input("interest_level", request.form.get("interest_level", ""))
        notes = request.form.get("notes", "").strip()

        assigned_to = current_user.user_id if current_user.role == COUNSELLOR else None

        new_lead = Lead(
            student_name=student_name,
            phone=phone,
            city=city,
            school_id=school_id,
            coaching_id=coaching_id,
            course_interest=course_interest,
            lead_source=lead_source,
            interest_level=interest_level,
            notes=notes,
            lead_score=0,
            status="new",
            organization_id=organization_id,
            assigned_to=assigned_to,
        )

        db.session.add(new_lead)
        db.session.flush()
        lead_id = new_lead.lead_id

        recalculate_and_persist_score(db, lead_id)
        db.session.commit()

        return redirect("/leads")

    return render_template("add_lead.html", schools=schools, coachings=coachings)


@leads_bp.route('/leads/edit/<int:lead_id>', methods=['GET', 'POST'])
@login_required
def edit_lead(lead_id):
    """Edit an existing lead."""
    db = get_db()
    organization_id = current_user.organization_id

    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id, Lead.organization_id == organization_id).first()
    if lead is None:
        abort(404)

    if current_user.role == COUNSELLOR and lead.assigned_to != current_user.user_id:
        abort(403)

    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        course_interest = request.form.get("course_interest", "").strip()
        interest_level = normalize_form_input("interest_level", request.form.get("interest_level", ""))
        notes = request.form.get("notes", "").strip()

        existing = db.session.query(Lead).filter(Lead.phone == phone, Lead.lead_id != lead_id, Lead.organization_id == organization_id).first()
        if existing:
            return "Lead with this phone already exists"

        lead.student_name = student_name
        lead.phone = phone
        lead.city = city
        lead.course_interest = course_interest
        lead.interest_level = interest_level
        lead.notes = notes

        recalculate_and_persist_score(db, lead_id)
        db.session.commit()

        return redirect(f"/leads/{lead_id}")

    return render_template("edit_lead.html", lead=lead)


@leads_bp.route('/followups')
@login_required
def followups():
    db = get_db()
    today_dt = date.today()
    organization_id = current_user.organization_id

    today = (
        db.session.query(Lead.student_name, Lead.phone, Interaction.notes, Interaction.follow_up_date)
        .join(Lead, Interaction.lead_id == Lead.lead_id)
        .filter(Interaction.follow_up_date == today_dt, Lead.organization_id == organization_id)
        .filter(Lead.assigned_to == current_user.user_id if current_user.role == COUNSELLOR else True)
        .order_by(Interaction.follow_up_date)
        .all()
    )

    overdue = (
        db.session.query(Lead.student_name, Lead.phone, Interaction.notes, Interaction.follow_up_date)
        .join(Lead, Interaction.lead_id == Lead.lead_id)
        .filter(Interaction.follow_up_date < today_dt, Lead.organization_id == organization_id)
        .filter(Lead.assigned_to == current_user.user_id if current_user.role == COUNSELLOR else True)
        .order_by(Interaction.follow_up_date)
        .all()
    )

    upcoming = (
        db.session.query(Lead.student_name, Lead.phone, Interaction.notes, Interaction.follow_up_date)
        .join(Lead, Interaction.lead_id == Lead.lead_id)
        .filter(Interaction.follow_up_date > today_dt, Lead.organization_id == organization_id)
        .filter(Lead.assigned_to == current_user.user_id if current_user.role == COUNSELLOR else True)
        .order_by(Interaction.follow_up_date)
        .all()
    )

    return render_template("followups.html", today=today, overdue=overdue, upcoming=upcoming)

