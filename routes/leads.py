from flask import Blueprint, render_template, request, redirect, abort
from database.db_connection import get_db
from modules.scoring_engine import recalculate_and_persist_score
from utils.form_helpers import normalize_form_input

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/leads')
def lead_list():
    db = get_db()

    query = request.args.get("q")
    city = request.args.get("city")
    status = request.args.get("status")
    course = request.args.get("course")

    filters = []
    params = []

    if query:
        filters.append("(student_name LIKE ? OR phone LIKE ?)")
        params.extend((f"%{query}%", f"%{query}%"))
    if city:
        filters.append("city = ?")
        params.append(city)
    if status:
        filters.append("status = ?")
        params.append(status)
    if course:
        filters.append("course_interest = ?")
        params.append(course)

    if filters:
        where_clause = " WHERE " + " AND ".join(filters)
        leads = db.execute(f"""
            SELECT *
            FROM leads{where_clause}
            ORDER BY created_at DESC
        """, params).fetchall()
    else:
        leads = db.execute("""
            SELECT *
            FROM leads
            ORDER BY created_at DESC
        """).fetchall()

    return render_template("leads.html", leads=leads)


@leads_bp.route('/leads/<int:lead_id>')
def lead_detail(lead_id):
    db = get_db()

    lead = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_id = ?
    """, (lead_id,)).fetchone()

    if lead is None:
        abort(404)

    interactions = db.execute("""
        SELECT *
        FROM interactions
        WHERE lead_id = ?
        ORDER BY created_at DESC
    """, (lead_id,)).fetchall()

    return render_template(
        "lead_detail.html",
        lead=lead,
        interactions=interactions
    )


@leads_bp.route('/leads/add', methods=['GET','POST'])
def add_lead():
    db = get_db()

    schools = db.execute("""
        SELECT institution_id, name
        FROM institutions
        WHERE type='school'
    """).fetchall()

    coachings = db.execute("""
        SELECT institution_id, name
        FROM institutions
        WHERE type='coaching_center'
    """).fetchall()

    if request.method == "POST":

        student_name = request.form["student_name"]
        phone = request.form["phone"]
        # ✅ Validation
        if not student_name:
            return "Student name is required"
        
        if not phone:
            return "Phone number is required"
        
        # ✅ Duplicate check
        existing = db.execute("""
            SELECT * FROM leads
            WHERE phone = ?
        """, (phone,)).fetchone()
        
        if existing:
            return "Lead with this phone already exists"
        city = request.form["city"]
        school_id = normalize_form_input("school_id", request.form["school_id"])
        coaching_id = normalize_form_input("coaching_id", request.form["coaching_id"])
        course_interest = request.form["course_interest"]
        lead_source = request.form["lead_source"]
        interest_level = normalize_form_input("interest_level", request.form["interest_level"])
        notes = request.form["notes"]

        cursor = db.execute("""
            INSERT INTO leads
            (student_name, phone, city, school_id, coaching_id,
            course_interest, lead_source, interest_level, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_name,
            phone,
            city,
            school_id,
            coaching_id,
            course_interest,
            lead_source,
            interest_level,
            notes
        ))

        lead_id = cursor.lastrowid
        recalculate_and_persist_score(db, lead_id)
        db.commit()

        return redirect("/leads")

    return render_template(
        "add_lead.html",
        schools=schools,
        coachings=coachings
    )


@leads_bp.route('/leads/edit/<int:lead_id>', methods=['GET', 'POST'])
def edit_lead(lead_id):
    db = get_db()

    lead = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_id = ?
    """, (lead_id,)).fetchone()

    if lead is None:
        abort(404)

    if request.method == "POST":

        student_name = request.form["student_name"]
        phone = request.form["phone"]
        city = request.form["city"]
        course_interest = request.form["course_interest"]
        interest_level = normalize_form_input("interest_level", request.form["interest_level"])
        notes = request.form["notes"]

        existing = db.execute("""
            SELECT * FROM leads
            WHERE phone = ? AND lead_id != ?
        """, (phone, lead_id)).fetchone()

        if existing:
            return "Lead with this phone already exists"

        db.execute("""
            UPDATE leads
            SET student_name = ?, phone = ?, city = ?,
                course_interest = ?, interest_level = ?, notes = ?
            WHERE lead_id = ?
        """, (
            student_name,
            phone,
            city,
            course_interest,
            interest_level,
            notes,
            lead_id
        ))

        recalculate_and_persist_score(db, lead_id)
        db.commit()

        return redirect(f"/leads/{lead_id}")

    return render_template("edit_lead.html", lead=lead)


@leads_bp.route('/followups')
def followups():
    db = get_db()

    today = db.execute("""
        SELECT l.student_name, l.phone, i.notes, i.follow_up_date
        FROM interactions i
        JOIN leads l ON i.lead_id = l.lead_id
        WHERE i.follow_up_date = DATE('now')
        ORDER BY i.follow_up_date
    """).fetchall()

    overdue = db.execute("""
        SELECT l.student_name, l.phone, i.notes, i.follow_up_date
        FROM interactions i
        JOIN leads l ON i.lead_id = l.lead_id
        WHERE i.follow_up_date < DATE('now')
        ORDER BY i.follow_up_date
    """).fetchall()

    upcoming = db.execute("""
        SELECT l.student_name, l.phone, i.notes, i.follow_up_date
        FROM interactions i
        JOIN leads l ON i.lead_id = l.lead_id
        WHERE i.follow_up_date > DATE('now')
        ORDER BY i.follow_up_date
    """).fetchall()

    return render_template(
        "followups.html",
        today=today,
        overdue=overdue,
        upcoming=upcoming
    )
