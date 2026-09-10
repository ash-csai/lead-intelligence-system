"""Institutions routes using SQLAlchemy ORM."""

from flask import Blueprint, render_template, request, redirect, abort
from flask_login import login_required, current_user
from database.db_connection import get_db
from database.models import Institution, Lead
from sqlalchemy import func
from utils.permissions import require_admin, ADMIN, MANAGER, COUNSELLOR

institutions_bp = Blueprint('institutions', __name__)


@institutions_bp.route('/institutions/analytics')
@login_required
def institution_analytics():
    db = get_db()
    organization_id = current_user.organization_id

    school_stats = (
        db.session.query(Institution.name, func.count(Lead.lead_id).label("total_leads"))
        .outerjoin(Lead, Lead.school_id == Institution.institution_id)
        .filter(Institution.type == 'school', Institution.organization_id == organization_id)
        .group_by(Institution.institution_id)
        .order_by(func.count(Lead.lead_id).desc())
        .all()
    )

    coaching_stats = (
        db.session.query(Institution.name, func.count(Lead.lead_id).label("total_leads"))
        .outerjoin(Lead, Lead.coaching_id == Institution.institution_id)
        .filter(Institution.type == 'coaching_center', Institution.organization_id == organization_id)
        .group_by(Institution.institution_id)
        .order_by(func.count(Lead.lead_id).desc())
        .all()
    )

    return render_template("institution_analytics.html", school_stats=school_stats, coaching_stats=coaching_stats)


@institutions_bp.route('/institutions')
@login_required
def institutions():
    db = get_db()
    organization_id = current_user.organization_id

    insts = (
        db.session.query(Institution)
        .filter(Institution.organization_id == organization_id)
        .order_by(Institution.created_at.desc())
        .all()
    )

    return render_template("institutions.html", institutions=insts)


@institutions_bp.route('/institutions/add', methods=['GET', 'POST'])
@login_required
def add_institution():
    db = get_db()
    organization_id = current_user.organization_id

    if current_user.role != ADMIN:
        abort(403)

    if request.method == "POST":
        name = request.form.get("name")
        type = request.form.get("type")
        city = request.form.get("city")
        contact_person = request.form.get("contact_person")
        contact_phone = request.form.get("contact_phone")
        notes = request.form.get("notes")

        new_inst = Institution(
            name=name,
            type=type,
            city=city,
            contact_person=contact_person,
            contact_phone=contact_phone,
            notes=notes,
            organization_id=organization_id,
        )
        db.session.add(new_inst)
        db.session.commit()

        return redirect("/institutions")

    return render_template("add_institution.html")
