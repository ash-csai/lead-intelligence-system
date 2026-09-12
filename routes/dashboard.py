from flask import Blueprint, render_template
from flask_login import login_required, current_user
from database.db_connection import get_db
from database.models import Lead, User
from sqlalchemy import func, case, and_
from modules.analytics_engine import (
    get_pipeline_counts,
    get_upcoming_followups,
    get_lead_buckets,
    build_priority_suggestions,
    find_neglected_leads,
)
from lead_intelligence.scoring import HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD
from utils.permissions import COUNSELLOR

dashboard_bp = Blueprint('dashboard', __name__)


def build_counsellor_breakdown(db, organization_id):
    """Return a lightweight per-counsellor lead distribution using existing assigned_to and lead_score data."""
    rows = (
        db.session.query(
            User.user_id.label("counsellor_id"),
            User.name.label("counsellor_name"),
            func.count(Lead.lead_id).label("total"),
            func.sum(case((Lead.lead_score >= HOT_LEAD_THRESHOLD, 1), else_=0)).label("hot"),
            func.sum(case((and_(Lead.lead_score >= WARM_LEAD_THRESHOLD, Lead.lead_score < HOT_LEAD_THRESHOLD), 1), else_=0)).label("warm"),
            func.sum(case((Lead.lead_score < WARM_LEAD_THRESHOLD, 1), else_=0)).label("cold"),
        )
        .outerjoin(Lead, and_(Lead.assigned_to == User.user_id, Lead.organization_id == organization_id))
        .filter(User.organization_id == organization_id, User.role == COUNSELLOR)
        .group_by(User.user_id, User.name)
        .order_by(User.name.asc())
        .all()
    )

    breakdown = []
    for row in rows:
        breakdown.append({
            "user_id": row.counsellor_id,
            "name": row.counsellor_name,
            "total": row.total or 0,
            "hot": row.hot or 0,
            "warm": row.warm or 0,
            "cold": row.cold or 0,
        })

    return breakdown


@dashboard_bp.route('/')
@login_required
def dashboard():
    db = get_db()
    organization_id = current_user.organization_id

    counts = get_pipeline_counts(db, organization_id=organization_id, user=current_user)
    upcoming = get_upcoming_followups(db, organization_id=organization_id, user=current_user)
    hot_leads, warm_leads, cold_leads = get_lead_buckets(db, organization_id=organization_id, user=current_user)
    urgent = build_priority_suggestions(db, organization_id=organization_id, user=current_user)
    inactive = find_neglected_leads(db, organization_id=organization_id, user=current_user)

    if current_user.role == COUNSELLOR:
        view_title = "Your leads"
        counsellor_breakdown = []
    else:
        view_title = "Team overview"
        counsellor_breakdown = build_counsellor_breakdown(db, organization_id)

    return render_template(
        "dashboard.html",
        new=counts["new"],
        contacted=counts["contacted"],
        interested=counts["interested"],
        applied=counts["applied"],
        admitted=counts["admitted"],
        lost=counts["lost"],
        total=counts["total"],
        upcoming=upcoming,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        urgent=urgent,
        inactive=inactive,
        view_title=view_title,
        counsellor_breakdown=counsellor_breakdown,
    )


@dashboard_bp.route('/analytics')
@login_required
def analytics():
    db = get_db()
    organization_id = current_user.organization_id

    city_stats = [
        {"city": city, "total": total}
        for city, total in db.session.query(
            Lead.city,
            func.count(Lead.lead_id)
        )
        .filter(Lead.organization_id == organization_id)
        .filter(Lead.assigned_to == current_user.user_id if current_user.role == COUNSELLOR else True)
        .group_by(Lead.city)
        .order_by(func.count(Lead.lead_id).desc())
        .all()
    ]

    source_stats = [
        {"lead_source": lead_source, "total": total}
        for lead_source, total in db.session.query(
            Lead.lead_source,
            func.count(Lead.lead_id)
        )
        .filter(Lead.organization_id == organization_id)
        .filter(Lead.assigned_to == current_user.user_id if current_user.role == COUNSELLOR else True)
        .group_by(Lead.lead_source)
        .order_by(func.count(Lead.lead_id).desc())
        .all()
    ]

    status_stats = [
        {"status": status, "total": total}
        for status, total in db.session.query(
            Lead.status,
            func.count(Lead.lead_id)
        )
        .filter(Lead.organization_id == organization_id)
        .filter(Lead.assigned_to == current_user.user_id if current_user.role == COUNSELLOR else True)
        .group_by(Lead.status)
        .all()
    ]

    return render_template(
        "analytics.html",
        city_stats=city_stats,
        source_stats=source_stats,
        status_stats=status_stats,
    )
