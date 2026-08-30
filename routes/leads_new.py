"""Leads routes using SQLAlchemy ORM."""

from flask import Blueprint, render_template, request, redirect, abort
from database.db_connection import get_db
from database.models import Lead, Institution
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input
from sqlalchemy import or_

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/leads')
def lead_list():
    """List all leads with optional filtering by query, city, status, course."""
    db = get_db()
    
    query = request.args.get("q")
    city = request.args.get("city")
    status = request.args.get("status")
    course = request.args.get("course")
    
    # Start with base query
    leads_query = db.session.query(Lead).order_by(Lead.created_at.desc())
    
    # Apply filters
    if query:
        search_term = f"%{query}%"
        leads_query = leads_query.filter(
            or_(
                Lead.student_name.ilike(search_term),
                Lead.phone.ilike(search_term)
            )
        )
    if city:
        leads_query = leads_query.filter(Lead.city == city)
    if status:
        leads_query = leads_query.filter(Lead.status == status)
    if course:
        leads_query = leads_query.filter(Lead.course_interest == course)
    
    leads = leads_query.all()
    
    return render_template("leads.html", leads=leads)


@leads_bp.route('/leads/<int:lead_id>')
def lead_detail(lead_id):
    """Show details for a specific lead and its interactions."""
    db = get_db()
    
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
    
    if lead is None:
        abort(404)
    
    # Interactions are eager-loaded via the relationship
    interactions = lead.interactions
    
    return render_template(
        "lead_detail.html",
        lead=lead,
        interactions=interactions
    )


@leads_bp.route('/leads/add', methods=['GET', 'POST'])
def add_lead():
    """Add a new lead."""
    db = get_db()
    
    # Get schools and coaching centers for the form
    schools = db.session.query(Institution).filter(
        Institution.type == 'school'
    ).all()
    
    coachings = db.session.query(Institution).filter(
        Institution.type == 'coaching_center'
    ).all()
    
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        phone = request.form.get("phone", "").strip()
        
        # Validation
        if not student_name:
            return "Student name is required"
        if not phone:
            return "Phone number is required"
        
        # Check for duplicate phone
        existing = db.session.query(Lead).filter(Lead.phone == phone).first()
        if existing:
            return "Lead with this phone already exists"
        
        # Get form data
        city = request.form.get("city", "").strip()
        school_id = normalize_form_input("school_id", request.form.get("school_id", ""))
        coaching_id = normalize_form_input("coaching_id", request.form.get("coaching_id", ""))
        course_interest = request.form.get("course_interest", "").strip()
        lead_source = request.form.get("lead_source", "").strip()
        interest_level = normalize_form_input("interest_level", request.form.get("interest_level", ""))
        notes = request.form.get("notes", "").strip()
        
        # Create new lead
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
            status="new"
        )
        
        db.session.add(new_lead)
        db.session.flush()  # Get the lead_id without committing
        
        lead_id = new_lead.lead_id
        
        # Recalculate score
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
        
        return redirect("/leads")
    
    return render_template(
        "add_lead.html",
        schools=schools,
        coachings=coachings
    )


@leads_bp.route('/leads/edit/<int:lead_id>', methods=['GET', 'POST'])
def edit_lead(lead_id):
    """Edit an existing lead."""
    db = get_db()
    
    lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
    
    if lead is None:
        abort(404)
    
    if request.method == "POST":
        student_name = request.form.get("student_name", "").strip()
        phone = request.form.get("phone", "").strip()
        city = request.form.get("city", "").strip()
        course_interest = request.form.get("course_interest", "").strip()
        interest_level = normalize_form_input("interest_level", request.form.get("interest_level", ""))
        notes = request.form.get("notes", "").strip()
        
        # Check for duplicate phone (excluding current lead)
        existing = db.session.query(Lead).filter(
            Lead.phone == phone,
            Lead.lead_id != lead_id
        ).first()
        
        if existing:
            return "Lead with this phone already exists"
        
        # Update lead
        lead.student_name = student_name
        lead.phone = phone
        lead.city = city
        lead.course_interest = course_interest
        lead.interest_level = interest_level
        lead.notes = notes
        
        # Recalculate score (might change if interest_level changed)
        recalculate_and_persist_score(db, lead_id)
        db.session.commit()
        
        return redirect(f"/leads/{lead_id}")
    
    return render_template("edit_lead.html", lead=lead)
