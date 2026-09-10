"""Institutions routes using SQLAlchemy ORM."""

from flask import Blueprint, render_template, request, redirect
from database.db_connection import get_db
from database.models import Institution, Lead
from sqlalchemy import func

institutions_bp = Blueprint('institutions', __name__)


@institutions_bp.route('/institutions/analytics')
def institution_analytics():
    db = get_db()

    school_stats = (
        db.session.query(
            Institution.name,
            func.count(Lead.lead_id).label("total_leads")
        )
        .outerjoin(Lead, Lead.school_id == Institution.institution_id)
        .filter(Institution.type == 'school')
        .group_by(Institution.institution_id)
        .order_by(func.count(Lead.lead_id).desc())
        .all()
    )

    coaching_stats = (
        db.session.query(
            Institution.name,
            func.count(Lead.lead_id).label("total_leads")
        )
        .outerjoin(Lead, Lead.coaching_id == Institution.institution_id)
        .filter(Institution.type == 'coaching_center')
        .group_by(Institution.institution_id)
        .order_by(func.count(Lead.lead_id).desc())
        .all()
    )

    return render_template(
        "institution_analytics.html",
        school_stats=school_stats,
        coaching_stats=coaching_stats
    )


@institutions_bp.route('/institutions')
def institutions():
    db = get_db()

    insts = (
        db.session.query(Institution)
        .order_by(Institution.created_at.desc())
        .all()
    )

    return render_template(
        "institutions.html",
        institutions=insts
    )


@institutions_bp.route('/institutions/add', methods=['GET', 'POST'])
def add_institution():
    db = get_db()

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
            notes=notes
        )
        db.session.add(new_inst)
        db.session.commit()

        return redirect("/institutions")

    return render_template("add_institution.html")
