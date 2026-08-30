"""Analytics engine using SQLAlchemy ORM."""

from datetime import datetime
from sqlalchemy import func, and_
from lead_intelligence.scoring import HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD
from lead_intelligence.priority import build_priority_details
from database.models import Lead, Interaction


def get_pipeline_counts(db):
    """Get counts of leads by status."""
    counts = {
        "new": 0,
        "contacted": 0,
        "interested": 0,
        "applied": 0,
        "admitted": 0,
        "lost": 0,
    }

    # Query leads grouped by status
    status_counts = (
        db.session.query(Lead.status, func.count(Lead.lead_id).label("total"))
        .group_by(Lead.status)
        .all()
    )

    for status, total in status_counts:
        if status in counts:
            counts[status] = total

    counts["total"] = db.session.query(func.count(Lead.lead_id)).scalar() or 0
    return counts


def get_upcoming_followups(db, limit=5):
    """Get upcoming follow-ups (next 5 by default)."""
    today = datetime.now().date()
    
    # Find interactions with future follow-up dates
    followups = (
        db.session.query(Lead.student_name, Interaction.follow_up_date)
        .join(Interaction, Lead.lead_id == Interaction.lead_id)
        .filter(
            and_(
                Interaction.follow_up_date.isnot(None),
                Interaction.follow_up_date >= today,
            )
        )
        .order_by(Interaction.follow_up_date.asc())
        .limit(limit)
        .all()
    )

    # Convert to dict-like objects for template compatibility
    return [{"student_name": name, "follow_up_date": date} for name, date in followups]


def get_lead_buckets(db):
    """Get leads categorized as hot, warm, and cold by score."""
    hot_leads = (
        db.session.query(Lead)
        .filter(Lead.lead_score >= HOT_LEAD_THRESHOLD)
        .order_by(Lead.lead_score.desc())
        .all()
    )

    warm_leads = (
        db.session.query(Lead)
        .filter(
            and_(
                Lead.lead_score >= WARM_LEAD_THRESHOLD,
                Lead.lead_score < HOT_LEAD_THRESHOLD,
            )
        )
        .order_by(Lead.lead_score.desc())
        .all()
    )

    cold_leads = (
        db.session.query(Lead)
        .filter(Lead.lead_score < WARM_LEAD_THRESHOLD)
        .order_by(Lead.lead_score.desc())
        .all()
    )

    return hot_leads, warm_leads, cold_leads


def build_priority_suggestions(db, today=None):
    """Build priority suggestions for leads with upcoming follow-ups."""
    if today is None:
        today = datetime.now().date()

    # Find leads with follow-up dates, getting the earliest one per lead
    priority_leads_subquery = (
        db.session.query(
            Lead.lead_id,
            func.min(Interaction.follow_up_date).label("next_followup"),
        )
        .outerjoin(Interaction, Lead.lead_id == Interaction.lead_id)
        .filter(Interaction.follow_up_date.isnot(None))
        .group_by(Lead.lead_id)
        .having(func.min(Interaction.follow_up_date).isnot(None))
        .subquery()
    )

    # Get full lead records with their next follow-up dates
    priority_leads = (
        db.session.query(Lead, priority_leads_subquery.c.next_followup)
        .join(priority_leads_subquery, Lead.lead_id == priority_leads_subquery.c.lead_id)
        .all()
    )

    urgent = []

    # Get last interaction for each lead
    last_action_lookup = {}
    for lead, _ in priority_leads:
        last_interaction = (
            db.session.query(Interaction.interaction_type)
            .filter(Interaction.lead_id == lead.lead_id)
            .order_by(Interaction.created_at.desc())
            .first()
        )
        if last_interaction:
            last_action_lookup[lead.lead_id] = last_interaction[0]

    # Build priority details for each lead
    for lead, next_followup in priority_leads:
        if next_followup:
            # Create a dict-like object with the lead data and next_followup
            lead_dict = {
                "lead_id": lead.lead_id,
                "student_name": lead.student_name,
                "phone": lead.phone,
                "city": lead.city,
                "school_id": lead.school_id,
                "coaching_id": lead.coaching_id,
                "course_interest": lead.course_interest,
                "lead_source": lead.lead_source,
                "interest_level": lead.interest_level,
                "lead_score": lead.lead_score,
                "status": lead.status,
                "created_at": lead.created_at,
                "notes": lead.notes,
                "next_followup": next_followup.strftime("%Y-%m-%d"),
            }
            
            priority_details = build_priority_details(
                lead_dict,
                last_action=last_action_lookup.get(lead.lead_id),
                today=today,
            )
            urgent.append(priority_details)

    # Sort by priority score
    urgent = sorted(urgent, key=lambda x: x["priority_score"], reverse=True)
    return urgent


def find_neglected_leads(db):
    """Find leads that haven't had recent interactions."""
    # Get all leads with their last interaction date
    leads = db.session.query(Lead).all()
    inactive = []

    for lead in leads:
        # Get the most recent interaction for this lead
        last_interaction = (
            db.session.query(Interaction.created_at)
            .filter(Interaction.lead_id == lead.lead_id)
            .order_by(Interaction.created_at.desc())
            .first()
        )

        if last_interaction:
            last_date = last_interaction[0]
        else:
            last_date = lead.created_at

        days_idle = (datetime.now() - last_date).days

        if days_idle >= 3:
            lead_dict = {
                "lead_id": lead.lead_id,
                "student_name": lead.student_name,
                "phone": lead.phone,
                "city": lead.city,
                "school_id": lead.school_id,
                "coaching_id": lead.coaching_id,
                "course_interest": lead.course_interest,
                "lead_source": lead.lead_source,
                "interest_level": lead.interest_level,
                "lead_score": lead.lead_score,
                "status": lead.status,
                "created_at": lead.created_at,
                "notes": lead.notes,
                "days_idle": days_idle,
                "last_interaction": (
                    last_interaction[0].strftime("%Y-%m-%d %H:%M:%S")
                    if last_interaction
                    else lead.created_at.strftime("%Y-%m-%d %H:%M:%S")
                ),
            }
            inactive.append(lead_dict)

    # Sort by worst cases
    inactive = sorted(inactive, key=lambda x: x["days_idle"], reverse=True)
    return inactive

