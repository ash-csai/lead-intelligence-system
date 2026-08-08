from datetime import datetime
from .scoring import HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD


def calculate_priority_score(lead_score, days_diff):
    if days_diff <= 0:
        urgency_score = 50
    elif days_diff <= 2:
        urgency_score = 30
    else:
        urgency_score = 10

    return urgency_score + (lead_score or 0)


def build_priority_reasons(days_diff, lead_score):
    reasons = []
    if days_diff < 0:
        reasons.append("Overdue follow-up")
    elif days_diff == 0:
        reasons.append("Follow-up today")

    if lead_score and lead_score >= HOT_LEAD_THRESHOLD:
        reasons.append("High-value lead")

    if lead_score and lead_score < WARM_LEAD_THRESHOLD:
        reasons.append("Low engagement")

    return ", ".join(reasons)


def suggest_priority_action(days_diff, lead_score):
    if days_diff <= 0:
        return "Call immediately"
    if lead_score and lead_score >= HOT_LEAD_THRESHOLD:
        return "Push for application"
    if lead_score and lead_score >= WARM_LEAD_THRESHOLD:
        return "Follow-up (WhatsApp/Message)"
    return "Low priority — nurture slowly"


def build_priority_details(lead, last_action=None, today=None):
    if today is None:
        today = datetime.now().date()

    followup_date = datetime.strptime(lead["next_followup"], "%Y-%m-%d").date()
    days_diff = (followup_date - today).days
    lead_score = lead["lead_score"]

    priority_score = calculate_priority_score(lead_score, days_diff)
    reasons = build_priority_reasons(days_diff, lead_score)
    suggestion = suggest_priority_action(days_diff, lead_score)

    lead_dict = dict(lead)
    lead_dict["last_action"] = last_action
    lead_dict["priority_score"] = priority_score
    lead_dict["days_diff"] = days_diff
    lead_dict["reasons"] = reasons
    lead_dict["suggestion"] = suggestion

    return lead_dict
