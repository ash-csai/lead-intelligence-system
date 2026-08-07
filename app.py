from flask import Flask
from database.db_connection import close_db

# Import blueprints
from routes.dashboard import dashboard_bp
from routes.leads import leads_bp
from routes.interactions import interactions_bp
from routes.institutions import institutions_bp


def create_app():
    app = Flask(__name__)
    app.teardown_appcontext(close_db)

    # Register blueprints (keep original URLs)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(interactions_bp)
    app.register_blueprint(institutions_bp)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)

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

        db.execute("""
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

@app.route("/leads/<int:lead_id>")
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

@app.route("/leads/<int:lead_id>/add_interaction", methods=["POST"])
def add_interaction(lead_id):

    db = get_db()

    interaction_type = request.form["interaction_type"]
    notes = request.form["notes"]
    follow_up_date = normalize_form_input("follow_up_date", request.form["follow_up_date"])

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

    interactions = db.execute("""
        SELECT *
        FROM interactions
        WHERE lead_id = ?
        ORDER BY created_at DESC
    """, (lead_id,)).fetchall()

    new_score = calculate_lead_score(lead, interactions)

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
    follow_up_date = normalize_form_input("follow_up_date", request.form["follow_up_date"])

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

    city_stats = [dict(row) for row in db.execute("""
        SELECT city, COUNT(*) as total
        FROM leads
        GROUP BY city
        ORDER BY total DESC
    """).fetchall()]

    source_stats = [dict(row) for row in db.execute("""
        SELECT lead_source, COUNT(*) as total
        FROM leads
        GROUP BY lead_source
        ORDER BY total DESC
    """).fetchall()]

    status_stats = [dict(row) for row in db.execute("""
        SELECT status, COUNT(*) as total
        FROM leads
        GROUP BY status
    """).fetchall()]

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

@app.route("/quick_action/<int:lead_id>", methods=["POST"])
def quick_action(lead_id):

    db = get_db()

    action_type = request.form["action_type"]

    # Store as interaction
    db.execute("""
        INSERT INTO interactions (lead_id, interaction_type, notes)
        VALUES (?, ?, ?)
    """, (lead_id, action_type, "Quick action performed"))

    # 🔁 Recalculate score
    lead = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_id = ?
    """, (lead_id,)).fetchone()

    interactions = db.execute("""
        SELECT *
        FROM interactions
        WHERE lead_id = ?
        ORDER BY created_at DESC
    """, (lead_id,)).fetchall()

    new_score = calculate_lead_score(lead, interactions)

    db.execute("""
        UPDATE leads
        SET lead_score = ?
        WHERE lead_id = ?
    """, (new_score, lead_id))

    db.commit()

    return redirect("/")

@app.route("/leads/edit/<int:lead_id>", methods=["GET", "POST"])
def edit_lead(lead_id):

    db = get_db()

    lead = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_id = ?
    """, (lead_id,)).fetchone()

    if request.method == "POST":

        student_name = request.form["student_name"]
        phone = request.form["phone"]
        city = request.form["city"]
        course_interest = request.form["course_interest"]
        interest_level = normalize_form_input("interest_level", request.form["interest_level"])
        notes = request.form["notes"]

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

        db.commit()

        return redirect(f"/leads/{lead_id}")

    return render_template("edit_lead.html", lead=lead)    

if __name__ == "__main__":
    app.run(debug=True)