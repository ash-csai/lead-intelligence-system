from flask import Blueprint, render_template
from database.db_connection import get_db
from database.models import Lead
from sqlalchemy import func
from modules.analytics_engine import (
    get_pipeline_counts,
    get_upcoming_followups,
    get_lead_buckets,
    build_priority_suggestions,
    find_neglected_leads,
)

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def dashboard():
    db = get_db()

    counts = get_pipeline_counts(db)
    upcoming = get_upcoming_followups(db)
    hot_leads, warm_leads, cold_leads = get_lead_buckets(db)
    urgent = build_priority_suggestions(db)
    inactive = find_neglected_leads(db)

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
    )


@dashboard_bp.route('/analytics')
def analytics():
    db = get_db()

    city_stats = [
        {"city": city, "total": total}
        for city, total in db.session.query(
            Lead.city,
            func.count(Lead.lead_id)
        )
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
        .group_by(Lead.status)
        .all()
    ]

    return render_template(
        "analytics.html",
        city_stats=city_stats,
        source_stats=source_stats,
        status_stats=status_stats,
    )
