from flask import Flask, render_template, request, redirect
from database.db_connection import get_db
import sqlite3
from datetime import datetime

app = Flask(__name__)

def calculate_lead_score(lead):

    score = 0

    # 🎯 1. Interest Level (base weight)
    if lead["interest_level"] == "high":
        score += 30
    elif lead["interest_level"] == "medium":
        score += 20
    else:
        score += 10

    db = get_db()

    interactions = db.execute("""
        SELECT *
        FROM interactions
        WHERE lead_id = ?
        ORDER BY created_at DESC
    """, (lead["lead_id"],)).fetchall()

    # 🔁 2. Interaction Frequency
    score += len(interactions) * 5

    # ⏱ 3. Recency Boost
    if interactions:
        last_interaction = interactions[0]["created_at"]
        last_date = datetime.strptime(last_interaction, "%Y-%m-%d %H:%M:%S")

        days_gap = (datetime.now() - last_date).days

        if days_gap <= 2:
            score += 25
        elif days_gap <= 7:
            score += 15
        elif days_gap <= 14:
            score += 5
        else:
            score -= 10   # cold lead

    # 🎬 4. Interaction Type Weight
    for i in interactions:
        if i["interaction_type"] == "application":
            score += 20
        elif i["interaction_type"] == "visit":
            score += 10
        elif i["interaction_type"] == "call":
            score += 5

    # 🏁 5. Status Weight
    if lead["status"] == "applied":
        score += 25
    elif lead["status"] == "interested":
        score += 15
    elif lead["status"] == "contacted":
        score += 5

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

    hot_leads = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_score >= 70
        ORDER BY lead_score DESC
    """).fetchall()

    warm_leads = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_score BETWEEN 40 AND 69
        ORDER BY lead_score DESC
    """).fetchall()

    cold_leads = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_score < 40
        ORDER BY lead_score DESC
    """).fetchall()

    today = datetime.now().date()

    priority_leads = db.execute("""
        SELECT l.*, MAX(i.follow_up_date) as next_followup
        FROM leads l
        LEFT JOIN interactions i ON l.lead_id = i.lead_id
        GROUP BY l.lead_id
        HAVING next_followup IS NOT NULL
    """).fetchall()
    urgent = []

    inactive_leads = db.execute("""
        SELECT l.*, MAX(i.created_at) as last_interaction
        FROM leads l
        LEFT JOIN interactions i ON l.lead_id = i.lead_id
        GROUP BY l.lead_id
    """).fetchall()

    for lead in priority_leads:
        if lead["next_followup"]:
            followup_date = datetime.strptime(lead["next_followup"], "%Y-%m-%d").date()

            days_diff = (followup_date - today).days

            # 🎯 Priority Logic
            if days_diff <= 0:
                urgency_score = 50   # overdue or today
            elif days_diff <= 2:
                urgency_score = 30
            else:
                urgency_score = 10

            total_priority = urgency_score + (lead["lead_score"] or 0)

            lead_dict = dict(lead)
            lead_dict["priority_score"] = total_priority
            lead_dict["days_diff"] = days_diff

            # 🧠 Reason Builder
            reasons = []

            if days_diff < 0:
                reasons.append("Overdue follow-up")
            elif days_diff == 0:
                reasons.append("Follow-up today")

            if lead["lead_score"] and lead["lead_score"] >= 70:
                reasons.append("High-value lead")

            if lead["lead_score"] and lead["lead_score"] < 40:
                reasons.append("Low engagement")

            lead_dict["reasons"] = ", ".join(reasons)

            urgent.append(lead_dict)

    # Sort by priority
    urgent = sorted(urgent, key=lambda x: x["priority_score"], reverse=True)

    inactive = []

    for lead in inactive_leads:

        if lead["last_interaction"]:
            last_date = datetime.strptime(lead["last_interaction"], "%Y-%m-%d %H:%M:%S")
            days_idle = (datetime.now() - last_date).days

            if days_idle >= 3:  # 🔥 threshold
                lead_dict = dict(lead)
                lead_dict["days_idle"] = days_idle
                inactive.append(lead_dict)

    #Sort by the worst cases
    inactive = sorted(inactive, key=lambda x: x["days_idle"], reverse=True)


    return render_template(
        "dashboard.html",
        new=new,
        contacted=contacted,
        interested=interested,
        applied=applied,
        admitted=admitted,
        lost=lost,
        total=total,
        upcoming=upcoming,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        urgent=urgent,
        inactive=inactive
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

    # Recalculate score after interaction
    lead = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_id = ?
    """, (lead_id,)).fetchone()

    new_score = calculate_lead_score(lead)

    db.execute("""
        UPDATE leads
        SET lead_score = ?
        WHERE lead_id = ?
    """, (new_score, lead_id))

    db.commit()

    return redirect(f"/leads/{lead_id}")

@app.route("/leads/update_status/<int:lead_id>", methods=["POST"])
def update_status(lead_id):

    db = get_db()

    new_status = request.form["status"]

    db.execute("""
        UPDATE leads
        SET status = ?
        WHERE lead_id = ?
    """, (new_status, lead_id))

    db.commit()

    return redirect(f"/leads/{lead_id}")

@app.route("/interactions/add/<int:lead_id>", methods=["POST"])
def auto_add_interaction(lead_id):

    db = get_db()

    interaction_type = request.form["interaction_type"]
    notes = request.form["notes"]
    follow_up_date = request.form["follow_up_date"]

    db.execute("""
        INSERT INTO interactions
        (lead_id, interaction_type, notes, follow_up_date)
        VALUES (?, ?, ?, ?)
    """, (lead_id, interaction_type, notes, follow_up_date))

    # 🔥 Smart Status Suggestion Logic
    if interaction_type == "call":
        db.execute("UPDATE leads SET status='contacted' WHERE lead_id=?", (lead_id,))
    elif interaction_type == "visit":
        db.execute("UPDATE leads SET status='interested' WHERE lead_id=?", (lead_id,))
    elif interaction_type == "application":
        db.execute("UPDATE leads SET status='applied' WHERE lead_id=?", (lead_id,))

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