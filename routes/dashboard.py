from flask import Blueprint, render_template
from flask_login import login_required, current_user
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
from utils.permissions import COUNSELLOR

dashboard_bp = Blueprint('dashboard', __name__)


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
