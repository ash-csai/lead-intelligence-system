from lead_intelligence.scoring import (
    HOT_LEAD_THRESHOLD,
    WARM_LEAD_THRESHOLD,
    calculate_lead_score,
)


def recalculate_and_persist_score(db, lead_id):
    """CRM-specific orchestration layer: fetch lead + interactions, score, persist.
    
    This function is NOT portable and stays in the CRM layer. It depends on the
    specific database schema (leads, interactions tables) and a live db connection.
    The pure scoring logic (calculate_lead_score) lives in lead_intelligence/.
    """
    lead = db.execute(
        "SELECT * FROM leads WHERE lead_id = ?",
        (lead_id,),
    ).fetchone()
    interactions = db.execute(
        "SELECT * FROM interactions WHERE lead_id = ? ORDER BY created_at DESC",
        (lead_id,),
    ).fetchall()
    score = calculate_lead_score(lead, interactions)
    db.execute(
        "UPDATE leads SET lead_score = ? WHERE lead_id = ?",
        (score, lead_id),
    )
    return score


__all__ = [
    "HOT_LEAD_THRESHOLD",
    "WARM_LEAD_THRESHOLD",
    "calculate_lead_score",
    "recalculate_and_persist_score",
]
