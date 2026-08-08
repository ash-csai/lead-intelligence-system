from datetime import datetime
from lead_intelligence.scoring import HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD
from lead_intelligence.priority import build_priority_details


def get_pipeline_counts(db):
    counts = {
        "new": 0,
        "contacted": 0,
        "interested": 0,
        "applied": 0,
        "admitted": 0,
        "lost": 0,
    }

    rows = db.execute("""
        SELECT status, COUNT(*) as total
        FROM leads
        GROUP BY status
    """).fetchall()

    for row in rows:
        counts[row[0]] = row[1]

    counts["total"] = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    return counts


def get_upcoming_followups(db, limit=5):
    return db.execute("""
        SELECT l.student_name, i.follow_up_date
        FROM interactions i
        JOIN leads l ON l.lead_id = i.lead_id
        WHERE i.follow_up_date IS NOT NULL
          AND i.follow_up_date >= DATE('now')
        ORDER BY i.follow_up_date ASC
        LIMIT ?
    """, (limit,)).fetchall()


def get_lead_buckets(db):
    hot_leads = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_score >= ?
        ORDER BY lead_score DESC
    """, (HOT_LEAD_THRESHOLD,)).fetchall()

    warm_leads = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_score >= ? AND lead_score < ?
        ORDER BY lead_score DESC
    """, (WARM_LEAD_THRESHOLD, HOT_LEAD_THRESHOLD)).fetchall()

    cold_leads = db.execute("""
        SELECT *
        FROM leads
        WHERE lead_score < ?
        ORDER BY lead_score DESC
    """, (WARM_LEAD_THRESHOLD,)).fetchall()

    return hot_leads, warm_leads, cold_leads


def build_priority_suggestions(db, today=None):
    if today is None:
        today = datetime.now().date()

    priority_leads = db.execute("""
        SELECT l.*, MIN(i.follow_up_date) as next_followup
        FROM leads l
        LEFT JOIN interactions i ON l.lead_id = i.lead_id
        WHERE i.follow_up_date IS NOT NULL
        GROUP BY l.lead_id
        HAVING next_followup IS NOT NULL
    """).fetchall()

    urgent = []

    priority_lead_ids = [lead["lead_id"] for lead in priority_leads]
    last_action_lookup = {}
    if priority_lead_ids:
        placeholders = ",".join(["?"] * len(priority_lead_ids))
        last_action_rows = db.execute(f"""
            SELECT i.lead_id, i.interaction_type
            FROM interactions i
            JOIN (
                SELECT lead_id, MAX(created_at) AS latest_created
                FROM interactions
                WHERE lead_id IN ({placeholders})
                GROUP BY lead_id
            ) latest ON i.lead_id = latest.lead_id AND i.created_at = latest.latest_created
        """, tuple(priority_lead_ids)).fetchall()
        for row in last_action_rows:
            last_action_lookup[row["lead_id"]] = row["interaction_type"]

    for lead in priority_leads:
        if lead["next_followup"]:
            lead_dict = build_priority_details(
                lead,
                last_action=last_action_lookup.get(lead["lead_id"]),
                today=today,
            )
            urgent.append(lead_dict)

    # Sort by priority
    urgent = sorted(urgent, key=lambda x: x["priority_score"], reverse=True)

    return urgent


def find_neglected_leads(db):
    inactive_leads = db.execute("""
        SELECT l.*, MAX(i.created_at) as last_interaction
        FROM leads l
        LEFT JOIN interactions i ON l.lead_id = i.lead_id
        GROUP BY l.lead_id
    """).fetchall()

    inactive = []

    for lead in inactive_leads:
        if lead["last_interaction"]:
            last_date = datetime.strptime(lead["last_interaction"], "%Y-%m-%d %H:%M:%S")
        else:
            last_date = datetime.strptime(lead["created_at"], "%Y-%m-%d %H:%M:%S")

        days_idle = (datetime.now() - last_date).days

        if days_idle >= 3:
            lead_dict = dict(lead)
            lead_dict["days_idle"] = days_idle
            inactive.append(lead_dict)

    # Sort by the worst cases
    inactive = sorted(inactive, key=lambda x: x["days_idle"], reverse=True)

    return inactive
