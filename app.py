from flask import Flask, render_template, request, redirect
from database.db_connection import get_db
import sqlite3

app = Flask(__name__)

def calculate_lead_score(lead):

    score = 0

    # Interest level scoring
    if lead["interest_level"] == "high":
        score += 40
    elif lead["interest_level"] == "medium":
        score += 25
    elif lead["interest_level"] == "low":
        score += 10

    # Status scoring
    if lead["status"] == "interested":
        score += 20
    elif lead["status"] == "applied":
        score += 30

    return score

@app.route("/")
def dashboard():

    db = get_db()

    new = db.execute("SELECT COUNT(*) FROM leads WHERE status='new'").fetchone()[0]
    contacted = db.execute("SELECT COUNT(*) FROM leads WHERE status='contacted'").fetchone()[0]
    interested = db.execute("SELECT COUNT(*) FROM leads WHERE status='interested'").fetchone()[0]
    applied = db.execute("SELECT COUNT(*) FROM leads WHERE status='applied'").fetchone()[0]
    admitted = db.execute("SELECT COUNT(*) FROM leads WHERE status='admitted'").fetchone()[0]
    lost = db.execute("SELECT COUNT(*) FROM leads WHERE status='lost'").fetchone()[0]

    total = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]

    upcoming = db.execute("""
        SELECT l.student_name, i.follow_up_date
        FROM interactions i
        JOIN leads l ON l.lead_id = i.lead_id
        WHERE i.follow_up_date IS NOT NULL
        ORDER BY i.follow_up_date ASC
        LIMIT 5
    """).fetchall()

    return render_template(
        "dashboard.html",
        new=new,
        contacted=contacted,
        interested=interested,
        applied=applied,
        admitted=admitted,
        lost=lost,
        total=total,
        upcoming=upcoming
    )

@app.route("/leads/add", methods=["GET","POST"])
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
        city = request.form["city"]
        school_id = request.form["school_id"]
        coaching_id = request.form["coaching_id"]
        course_interest = request.form["course_interest"]
        interest_level = request.form["interest_level"]
        notes = request.form["notes"]

        db.execute("""
            INSERT INTO leads
            (student_name, phone, city, school_id, coaching_id,
            course_interest, interest_level, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_name,
            phone,
            city,
            school_id,
            coaching_id,
            course_interest,
            interest_level,
            notes
        ))

        db.commit()

        return redirect("/leads")

    return render_template(
        "add_lead.html",
        schools=schools,
        coachings=coachings
    )

@app.route("/leads")
def lead_list():

    db = get_db()

    city = request.args.get("city")
    status = request.args.get("status")
    course = request.args.get("course")

    query = """
        SELECT lead_id, student_name, phone, city,
               course_interest, interest_level,
               status, created_at
        FROM leads
        WHERE 1=1
    """

    params = []

    if city:
        query += " AND city = ?"
        params.append(city)

    if status:
        query += " AND status = ?"
        params.append(status)

    if course:
        query += " AND course_interest = ?"
        params.append(course)

    query += " ORDER BY created_at DESC"

    leads = db.execute(query, params).fetchall()

    return render_template("leads.html", leads=leads)

@app.route("/leads/<int:lead_id>")
def lead_detail(lead_id):

    db = get_db()

    lead = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_id = ?
    """, (lead_id,)).fetchone()

    # Calculate lead score
    score = calculate_lead_score(lead)

    db.execute("""
        UPDATE leads
        SET lead_score = ?
        WHERE lead_id = ?
    """, (score, lead_id))

    db.commit()

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

@app.route("/leads/<int:lead_id>/add_interaction", methods=["POST"])
def add_interaction(lead_id):

    db = get_db()

    interaction_type = request.form["interaction_type"]
    notes = request.form["notes"]
    follow_up_date = request.form["follow_up_date"]

    db.execute("""
        INSERT INTO interactions
        (lead_id, interaction_type, notes, follow_up_date)
        VALUES (?, ?, ?, ?)
    """, (lead_id, interaction_type, notes, follow_up_date))

    db.commit()

    return redirect(f"/leads/{lead_id}")

@app.route("/followups")
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

@app.route("/analytics")
def analytics():

    db = get_db()

    city_stats = db.execute("""
        SELECT city, COUNT(*) as total
        FROM leads
        GROUP BY city
        ORDER BY total DESC
    """).fetchall()

    source_stats = db.execute("""
        SELECT lead_source, COUNT(*) as total
        FROM leads
        GROUP BY lead_source
        ORDER BY total DESC
    """).fetchall()

    status_stats = db.execute("""
        SELECT status, COUNT(*) as total
        FROM leads
        GROUP BY status
    """).fetchall()

    return render_template(
        "analytics.html",
        city_stats=city_stats,
        source_stats=source_stats,
        status_stats=status_stats
    )

@app.route("/institutions/analytics")
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

@app.route("/institutions")
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

@app.route("/institutions/add", methods=["GET","POST"])
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

if __name__ == "__main__":
    app.run(debug=True)