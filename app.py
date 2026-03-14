from flask import Flask, render_template, request, redirect
from database.db_connection import get_db
import sqlite3

app = Flask(__name__)


@app.route("/")
def dashboard():
    db = get_db()

    # Example counts
    new_leads = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status='new'"
    ).fetchone()[0]

    contacted = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status='contacted'"
    ).fetchone()[0]

    interested = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status='interested'"
    ).fetchone()[0]

    applied = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status='applied'"
    ).fetchone()[0]

    admitted = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status='admitted'"
    ).fetchone()[0]

    lost = db.execute(
        "SELECT COUNT(*) FROM leads WHERE status='lost'"
    ).fetchone()[0]

    return render_template(
        "dashboard.html",
        new=new_leads,
        contacted=contacted,
        interested=interested,
        applied=applied,
        admitted=admitted,
        lost=lost
    )

@app.route("/leads/add", methods=["GET", "POST"])
def add_lead():
    db = get_db()

    if request.method == "POST":

        student_name = request.form["student_name"]
        phone = request.form["phone"]
        city = request.form["city"]
        course_interest = request.form["course_interest"]
        interest_level = request.form["interest_level"]
        notes = request.form["notes"]

        db.execute("""
            INSERT INTO leads
            (student_name, phone, city, course_interest, interest_level, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_name, phone, city, course_interest, interest_level, notes))

        db.commit()

        return redirect("/")

    return render_template("add_lead.html")

@app.route("/leads")
def lead_list():

    db = get_db()

    leads = db.execute("""
        SELECT lead_id, student_name, phone, city,
               course_interest, interest_level,
               status, created_at
        FROM leads
        ORDER BY created_at DESC
    """).fetchall()

    return render_template("leads.html", leads=leads)

if __name__ == "__main__":
    app.run(debug=True)