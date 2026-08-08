from datetime import datetime
from modules.scoring_engine import HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD


def get_pipeline_counts(db):
    counts = {}
    counts["new"] = db.execute("SELECT COUNT(*) FROM leads WHERE status='new'").fetchone()[0]
    counts["contacted"] = db.execute("SELECT COUNT(*) FROM leads WHERE status='contacted'").fetchone()[0]
    counts["interested"] = db.execute("SELECT COUNT(*) FROM leads WHERE status='interested'").fetchone()[0]
    counts["applied"] = db.execute("SELECT COUNT(*) FROM leads WHERE status='applied'").fetchone()[0]
    counts["admitted"] = db.execute("SELECT COUNT(*) FROM leads WHERE status='admitted'").fetchone()[0]
    counts["lost"] = db.execute("SELECT COUNT(*) FROM leads WHERE status='lost'").fetchone()[0]
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
            followup_date = datetime.strptime(lead["next_followup"], "%Y-%m-%d").date()

            days_diff = (followup_date - today).days

            # Priority Logic
            if days_diff <= 0:
                urgency_score = 50
            elif days_diff <= 2:
                urgency_score = 30
            else:
                urgency_score = 10

            total_priority = urgency_score + (lead["lead_score"] or 0)

            lead_dict = dict(lead)

            lead_dict["last_action"] = last_action_lookup.get(lead["lead_id"])

            # Reason Builder
            reasons = []
            if days_diff < 0:
                reasons.append("Overdue follow-up")
            elif days_diff == 0:
                reasons.append("Follow-up today")

            if lead["lead_score"] and lead["lead_score"] >= HOT_LEAD_THRESHOLD:
                reasons.append("High-value lead")

            if lead["lead_score"] and lead["lead_score"] < WARM_LEAD_THRESHOLD:
                reasons.append("Low engagement")

            lead_dict["reasons"] = ", ".join(reasons)

            lead_dict["priority_score"] = total_priority
            lead_dict["days_diff"] = days_diff
            lead_dict["reasons"] = ", ".join(reasons)

            # Action Suggestion Engine
            suggestion = "Review manually"

            if lead_dict["days_diff"] <= 0:
                suggestion = "Call immediately"
            elif lead["lead_score"] and lead["lead_score"] >= HOT_LEAD_THRESHOLD:
                suggestion = "Push for application"
            elif lead["lead_score"] and lead["lead_score"] >= WARM_LEAD_THRESHOLD:
                suggestion = "Follow-up (WhatsApp/Message)"
            elif lead["lead_score"] < WARM_LEAD_THRESHOLD:
                suggestion = "Low priority — nurture slowly"

            lead_dict["suggestion"] = suggestion

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
