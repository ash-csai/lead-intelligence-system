"""Role and organization authorization helpers for the app.

Role permissions intentionally stay simple:
- Admin: full access within their organization.
- Manager: same org-wide visibility and action as Admin, but without user management.
- Counsellor: only sees and acts on leads assigned to their own user_id in the same organization.
"""

from flask import abort
from flask_login import current_user


ADMIN = "Admin"
MANAGER = "Manager"
COUNSELLOR = "Counsellor"


def normalize_role(role):
    if role in {ADMIN, MANAGER, COUNSELLOR}:
        return role
    return None


def is_org_user(user):
    return user and getattr(user, "organization_id", None) is not None


def user_can_access_lead(user, lead):
    """Return True when the logged-in user may view/act on a lead in the same org."""
    if not user or not lead:
        return False

    if getattr(lead, "organization_id", None) != getattr(user, "organization_id", None):
        return False

    if user.role in {ADMIN, MANAGER}:
        return True

    if user.role == COUNSELLOR:
        return getattr(lead, "assigned_to", None) == user.user_id

    return False


def require_lead_access(user, lead):
    """Validate role-specific access and raise 403 if the lead is not allowed.

    Missing lead records raise 404 before access logic.
    """
    if not user or not lead:
        abort(404)

    if lead.organization_id != user.organization_id:
        abort(403)

    if user.role == COUNSELLOR and lead.assigned_to != user.user_id:
        abort(403)

    # Admin and Manager pass through organization-wide access.
    return True


def require_admin(user):
    if not user or getattr(user, "role", None) != ADMIN:
        abort(403)


def scope_lead_query(query, user):
    """Apply the base organization lead query scope for the current authenticated user."""
    from database.models import Lead

    if not user:
        return query

    query = query.filter(Lead.organization_id == user.organization_id)
    if user.role == COUNSELLOR:
        query = query.filter(Lead.assigned_to == user.user_id)

    return query
