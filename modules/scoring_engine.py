from datetime import datetime

HOT_LEAD_THRESHOLD = 70
WARM_LEAD_THRESHOLD = 40


def calculate_lead_score(lead, interactions):
    score = 0

    # 🎯 1. Interest Level (base weight)
    if lead["interest_level"] == "high":
        score += 30
    elif lead["interest_level"] == "medium":
        score += 20
    else:
        score += 10

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
