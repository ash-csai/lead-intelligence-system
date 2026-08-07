from flask import Blueprint, render_template, request, redirect
from database.db_connection import get_db

institutions_bp = Blueprint('institutions', __name__)


@institutions_bp.route('/institutions/analytics')
def institution_analytics():
    db = get_db()

    school_stats = db.execute("""
        SELECT i.name, COUNT(l.lead_id) as total_leads
        FROM institutions i
        LEFT JOIN leads l ON l.school_id = i.institution_id
        WHERE i.type = 'school'
        GROUP BY i.institution_id
        ORDER BY total_leads DESC
    """).fetchall()

    coaching_stats = db.execute("""
        SELECT i.name, COUNT(l.lead_id) as total_leads
        FROM institutions i
        LEFT JOIN leads l ON l.coaching_id = i.institution_id
        WHERE i.type = 'coaching_center'
        GROUP BY i.institution_id
        ORDER BY total_leads DESC
    """).fetchall()

    return render_template(
        "institution_analytics.html",
        school_stats=school_stats,
        coaching_stats=coaching_stats
    )


@institutions_bp.route('/institutions')
def institutions():
    db = get_db()

    institutions = db.execute("""
        SELECT *
        FROM institutions
        ORDER BY created_at DESC
    """).fetchall()

    return render_template(
        "institutions.html",
        institutions=institutions
    )


@institutions_bp.route('/institutions/add', methods=['GET','POST'])
def add_institution():
    db = get_db()

    if request.method == "POST":

        name = request.form["name"]
        type = request.form["type"]
        city = request.form["city"]
        contact_person = request.form["contact_person"]
        contact_phone = request.form["contact_phone"]
        notes = request.form["notes"]

        db.execute("""
            INSERT INTO institutions
            (name, type, city, contact_person, contact_phone, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, type, city, contact_person, contact_phone, notes))

        db.commit()

        return redirect("/institutions")

    return render_template("add_institution.html")
