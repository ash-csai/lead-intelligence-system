"""Role and permission regression tests for the auth/permission layer."""

import pytest


class TestRolePermissionMatrix:
    """Role-based authorization should be enforceable through the app client."""

    def test_counsellor_forbidden_on_other_counsellor_lead(self, app):
        with app.app_context():
            from database.models import User, Lead, db
            from werkzeug.security import generate_password_hash

            # Create organization 1 test users.
            admin = User(name="Admin", email="admin2@example.com", role="Admin", organization_id=1)
            admin.set_password("secret")
            manager = User(name="Manager", email="manager@example.com", role="Manager", organization_id=1)
            manager.set_password("secret")
            counsellor_a = User(name="Counsellor A", email="counsellor_a@example.com", role="Counsellor", organization_id=1)
            counsellor_a.set_password("secret")
            counsellor_b = User(name="Counsellor B", email="counsellor_b@example.com", role="Counsellor", organization_id=1)
            counsellor_b.set_password("secret")

            db.session.add_all([admin, manager, counsellor_a, counsellor_b])
            db.session.flush()

            # Create a lead assigned to counsellor_b.
            other_lead = Lead(
                student_name="Other Counsellor Lead",
                phone="900-901-9020",
                city="Test City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                notes="Assigned outside",
                status="new",
                lead_score=0,
                organization_id=1,
                assigned_to=counsellor_b.user_id,
            )
            db.session.add(other_lead)
            db.session.commit()

            # Important: log counsellor_a in and hit detail endpoint with 403.
            client = app.test_client()
            with client:
                client.post("/login", data={"email": "counsellor_a@example.com", "password": "secret"}, follow_redirects=True)
                response = client.get(f"/leads/{other_lead.lead_id}")
                assert response.status_code == 403

    def test_manager_and_admin_can_see_all_org_leads(self, app):
        with app.app_context():
            from database.models import User, Lead, db
            db.session.query(Lead).delete()
            db.session.query(User).delete()
            db.session.commit()

            admin = User(name="Admin", email="admin-role@example.com", role="Admin", organization_id=1)
            admin.set_password("secret")
            manager = User(name="Manager", email="manager-role@example.com", role="Manager", organization_id=1)
            manager.set_password("secret")
            counsellor = User(name="Counsellor", email="counsellor-role@example.com", role="Counsellor", organization_id=1)
            counsellor.set_password("secret")
            db.session.add_all([admin, manager, counsellor])
            db.session.commit()

            lead = Lead(
                student_name="Role Visible Lead",
                phone="555-0100-1010",
                city="Test City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                notes="Owned by counsellor",
                status="new",
                lead_score=0,
                organization_id=1,
                assigned_to=counsellor.user_id,
            )
            db.session.add(lead)
            db.session.commit()

            client = app.test_client()

            login_resp = client.post("/login", data={"email": "admin-role@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)
            resp_admin = client.get(f"/leads/{lead.lead_id}")
            assert resp_admin.status_code == 200

            client.get("/logout")

            login_resp = client.post("/login", data={"email": "manager-role@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)
            resp_manager = client.get(f"/leads/{lead.lead_id}")
            assert resp_manager.status_code == 200
