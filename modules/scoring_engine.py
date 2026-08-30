from lead_intelligence.scoring import (
    HOT_LEAD_THRESHOLD,
    WARM_LEAD_THRESHOLD,
    calculate_lead_score,
)
from database.models import Lead, Interaction
from sqlalchemy import desc


def recalculate_and_persist_score(db, lead_id):
    """CRM-specific orchestration layer: fetch lead + interactions, score, persist.
    
    This function is NOT portable and stays in the CRM layer. It depends on the
    specific database schema (leads, interactions tables) and a live db connection.
    The pure scoring logic (calculate_lead_score) lives in lead_intelligence/.
    """
    # Fetch lead using SQLAlchemy
    lead_obj = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
    if not lead_obj:
        return None
    
    # Fetch interactions using SQLAlchemy, ordered by created_at DESC
    interaction_objs = (
        db.session.query(Interaction)
        .filter(Interaction.lead_id == lead_id)
        .order_by(desc(Interaction.created_at))
        .all()
    )
    
    # Convert to dicts for compatibility with calculate_lead_score
    lead_dict = {
        "lead_id": lead_obj.lead_id,
        "student_name": lead_obj.student_name,
        "phone": lead_obj.phone,
        "city": lead_obj.city,
        "school_id": lead_obj.school_id,
        "coaching_id": lead_obj.coaching_id,
        "course_interest": lead_obj.course_interest,
        "lead_source": lead_obj.lead_source,
        "interest_level": lead_obj.interest_level,
        "lead_score": lead_obj.lead_score,
        "status": lead_obj.status,
        "created_at": lead_obj.created_at,
        "notes": lead_obj.notes,
    }
    
    interactions_list = [
        {
            "interaction_id": i.interaction_id,
            "lead_id": i.lead_id,
            "interaction_type": i.interaction_type,
            "notes": i.notes,
            "follow_up_date": i.follow_up_date,
            "created_at": i.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for i in interaction_objs
    ]
    
    # Calculate new score
    score = calculate_lead_score(lead_dict, interactions_list)
    
    # Update lead score in database
    lead_obj.lead_score = score
    db.session.commit()
    
    return score


__all__ = [
    "HOT_LEAD_THRESHOLD",
    "WARM_LEAD_THRESHOLD",
    "calculate_lead_score",
    "recalculate_and_persist_score",
]

