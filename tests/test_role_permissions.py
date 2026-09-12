"""Role and permission regression tests for the auth/permission layer."""

import pytest


class TestRolePermissionMatrix:
    """Role-based authorization should be enforceable through the app client."""

    def test_admin_can_create_users_for_each_role_and_managers_and_counsellors_get_403(self, app):
        with app.app_context():
            from database.models import User, db
            db.session.query(User).delete()
            db.session.commit()

            admin = User(name="Admin", email="admin-team@example.com", role="Admin", organization_id=1, is_active=True)
            admin.set_password("secret")
            db.session.add(admin)
            db.session.commit()

            client = app.test_client()
            login_resp = client.post("/login", data={"email": "admin-team@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)

            for role in ["Admin", "Manager", "Counsellor"]:
                create_resp = client.post(
                    "/team",
                    data={
                        "name": f"{role} User",
                        "email": f"{role.lower()}-team@example.com",
                        "password": "secret",
                        "role": role,
                    },
                    follow_redirects=True,
                )
                assert create_resp.status_code == 200

            created = db.session.query(User).filter(User.organization_id == 1).all()
            assert any(user.role == "Admin" for user in created)
            assert any(user.role == "Manager" for user in created)
            assert any(user.role == "Counsellor" for user in created)

            client.get("/logout")

            manager = User(name="Manager", email="manager-team@example.com", role="Manager", organization_id=1, is_active=True)
            manager.set_password("secret")
            db.session.add(manager)
            db.session.commit()

            # Login as a member of the org but not Admin and assert team access is forbidden.
            login_resp = client.post("/login", data={"email": "manager-team@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)
            manager_team_resp = client.get("/team")
            assert manager_team_resp.status_code == 403

            client.get("/logout")

            counsellor = User(name="Counsellor", email="counsellor-team@example.com", role="Counsellor", organization_id=1, is_active=True)
            counsellor.set_password("secret")
            db.session.add(counsellor)
            db.session.commit()

            login_resp = client.post("/login", data={"email": "counsellor-team@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)
            counsellor_team_resp = client.get("/team")
            assert counsellor_team_resp.status_code == 403

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

    def test_counsellor_can_create_lead_and_see_it_in_own_lead_list(self, app):
        with app.app_context():
            from database.models import User, Lead, db
            db.session.query(Lead).delete()
            db.session.query(User).delete()
            db.session.commit()

            counsellor = User(name="Counsellor", email="counsellor-create@example.com", role="Counsellor", organization_id=1)
            counsellor.set_password("secret")
            db.session.add(counsellor)
            db.session.commit()

            client = app.test_client()
            login_resp = client.post(
                "/login",
                data={"email": "counsellor-create@example.com", "password": "secret"},
                follow_redirects=True,
            )
            assert login_resp.status_code in (200, 302)

            get_resp = client.get("/leads/add")
            assert get_resp.status_code == 200

            post_resp = client.post(
                "/leads/add",
                data={
                    "student_name": "Counsellor Created Lead",
                    "phone": "555-0100-1111",
                    "city": "Test City",
                    "school_id": "",
                    "coaching_id": "",
                    "course_interest": "Course",
                    "lead_source": "Website",
                    "interest_level": "high",
                    "notes": "Created by counsellor",
                },
                follow_redirects=True,
            )
            assert post_resp.status_code == 200

            created = db.session.query(Lead).filter(Lead.phone == "555-0100-1111", Lead.organization_id == 1).first()
            assert created is not None
            assert created.assigned_to == counsellor.user_id

            leads_resp = client.get("/leads")
            assert leads_resp.status_code == 200
            assert b"Counsellor Created Lead" in leads_resp.data
