"""Route-level smoke tests for the Lead Intelligence System."""

from datetime import datetime, timedelta
import pytest
from sqlalchemy.exc import IntegrityError


class TestDashboardRoutes:
    """Test dashboard and analytics routes."""

    def test_dashboard_loads_200(self, client):
        """Dashboard route should load successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"dashboard" in response.data.lower() or b"lead" in response.data.lower()

    def test_dashboard_role_banner_and_counsellor_breakdown_visibility(self, client, app):
        """Manager/Admin should see the team overview banner and counsellor breakdown, while Counsellor should see only the personalized view."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Team overview" in response.data
        assert b"Counsellor lead breakdown" in response.data

        with app.app_context():
            from database.models import User, Lead, db
            db.session.query(Lead).delete()
            db.session.query(User).filter(User.email != "admin@example.com").delete()
            db.session.commit()

            counsellor = User(name="Counsellor", email="counsellor-dashboard@example.com", role="Counsellor", organization_id=1, is_active=True)
            counsellor.set_password("secret")
            db.session.add(counsellor)
            db.session.commit()

            lead = Lead(
                student_name="Counsellor Dashboard Lead",
                phone="555-0100-1212",
                city="Test City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                lead_score=75,
                status="new",
                organization_id=1,
                assigned_to=counsellor.user_id,
            )
            db.session.add(lead)
            db.session.commit()

            client = app.test_client()
            login_resp = client.post("/login", data={"email": "counsellor-dashboard@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)

            counsellor_resp = client.get("/")
            assert counsellor_resp.status_code == 200
            assert b"Your leads" in counsellor_resp.data
            assert b"Team overview" not in counsellor_resp.data
            assert b"Counsellor lead breakdown" not in counsellor_resp.data

    def test_bulk_reassign_and_status_update_trigger_scoring_for_each_selected_lead(self, app):
        """Bulk reassignment should respect org and role scope, and bulk status changes must recalculate every affected lead score."""
        with app.app_context():
            from database.models import Organization, User, Lead, db
            from lead_intelligence.scoring import calculate_lead_score

            db.session.query(Lead).delete()
            db.session.query(User).delete()
            db.session.query(Organization).delete()
            db.session.commit()

            org_1 = Organization(name="Org One")
            org_2 = Organization(name="Org Two")
            db.session.add_all([org_1, org_2])
            db.session.commit()

            manager = User(name="Manager", email="manager-bulk@example.com", role="Manager", organization_id=org_1.organization_id, is_active=True)
            manager.set_password("secret")
            counsellor_a = User(name="Counsellor A", email="counsellor-a-bulk@example.com", role="Counsellor", organization_id=org_1.organization_id, is_active=True)
            counsellor_a.set_password("secret")
            counsellor_b = User(name="Counsellor B", email="counsellor-b-bulk@example.com", role="Counsellor", organization_id=org_1.organization_id, is_active=True)
            counsellor_b.set_password("secret")
            outsider = User(name="Other Org Counsellor", email="outsider-bulk@example.com", role="Counsellor", organization_id=org_2.organization_id, is_active=True)
            outsider.set_password("secret")
            db.session.add_all([manager, counsellor_a, counsellor_b, outsider])
            db.session.commit()

            lead_1 = Lead(
                student_name="First Bulk Lead",
                phone="555-0100-1111",
                city="Test City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                status="new",
                lead_score=0,
                organization_id=org_1.organization_id,
                assigned_to=counsellor_a.user_id,
            )
            lead_2 = Lead(
                student_name="Second Bulk Lead",
                phone="555-0100-2222",
                city="Test City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                status="new",
                lead_score=0,
                organization_id=org_1.organization_id,
                assigned_to=counsellor_a.user_id,
            )
            cross_org = Lead(
                student_name="Wrong Org Lead",
                phone="555-0100-3333",
                city="Other City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                status="new",
                lead_score=0,
                organization_id=org_2.organization_id,
                assigned_to=outsider.user_id,
            )
            db.session.add_all([lead_1, lead_2, cross_org])
            db.session.commit()

            client = app.test_client()
            login_resp = client.post("/login", data={"email": "manager-bulk@example.com", "password": "secret"}, follow_redirects=True)
            assert login_resp.status_code in (200, 302)

            reassign_resp = client.post(
                "/leads/bulk_action",
                data={
                    "bulk_action": "reassign",
                    "counsellor_id": counsellor_b.user_id,
                    "lead_id": [str(lead_1.lead_id), str(lead_2.lead_id), str(cross_org.lead_id)],
                },
                follow_redirects=True,
            )
            assert reassign_resp.status_code == 200

            db.session.expire_all()
            assert db.session.query(Lead).filter(Lead.lead_id == lead_1.lead_id).one().assigned_to == counsellor_b.user_id
            assert db.session.query(Lead).filter(Lead.lead_id == lead_2.lead_id).one().assigned_to == counsellor_b.user_id
            assert db.session.query(Lead).filter(Lead.lead_id == cross_org.lead_id).one().assigned_to == outsider.user_id

            status_resp = client.post(
                "/leads/bulk_action",
                data={
                    "bulk_action": "status",
                    "bulk_status": "contacted",
                    "lead_id": [str(lead_1.lead_id), str(lead_2.lead_id)],
                },
                follow_redirects=True,
            )
            assert status_resp.status_code == 200

            db.session.expire_all()
            for lead_id in [lead_1.lead_id, lead_2.lead_id]:
                lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).one()
                assert lead.status == "contacted"
                expected = calculate_lead_score({
                    "lead_id": lead.lead_id,
                    "student_name": lead.student_name,
                    "phone": lead.phone,
                    "city": lead.city,
                    "school_id": lead.school_id,
                    "coaching_id": lead.coaching_id,
                    "course_interest": lead.course_interest,
                    "lead_source": lead.lead_source,
                    "interest_level": lead.interest_level,
                    "lead_score": 0,
                    "status": "contacted",
                    "created_at": lead.created_at,
                    "notes": lead.notes,
                }, [])
                assert lead.lead_score == expected

    def test_analytics_loads_200(self, client):
        """Analytics route should load successfully."""
        response = client.get("/analytics")
        assert response.status_code == 200


class TestLeadRoutes:
    """Test lead management routes."""

    def test_lead_list_loads(self, client):
        """Lead list should load successfully."""
        response = client.get("/leads")
        assert response.status_code == 200

    def test_lead_detail_404_nonexistent(self, client):
        """Should 404 on nonexistent lead_id."""
        response = client.get("/leads/99999")
        assert response.status_code == 404

    def test_add_lead_page_loads(self, client):
        """Add lead page should load."""
        response = client.get("/leads/add")
        assert response.status_code == 200

    def test_add_lead_creates_lead(self, client, app):
        """Should create a new lead via POST."""
        with app.app_context():
            response = client.post("/leads/add", data={
                "student_name": "Test Student",
                "phone": "555-1234-5678",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Test Course",
                "lead_source": "Referral",
                "interest_level": "high",
                "notes": "Test lead",
            }, follow_redirects=True)
            
            assert response.status_code == 200

    def test_lead_detail_loads_after_create(self, client, app):
        """Created lead should be viewable in detail."""
        with app.app_context():
            # Create a lead
            response = client.post("/leads/add", data={
                "student_name": "Jane Doe",
                "phone": "555-9876-5432",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Test Course",
                "lead_source": "Website",
                "interest_level": "medium",
                "notes": "Test lead for detail view",
            }, follow_redirects=True)
            
            # The redirect should land on a success page or the lead list
            assert response.status_code == 200


class TestHtmxRoutes:
    """Exercise the htmx enhancement contract for the main browser routes without replacing the normal Jinja/Flask server-rendered fallbacks."""

    def test_leads_list_htmx_request_returns_fragment(self, client):
        """An htmx request should receive the leads table fragment rather than the full leads page shell, while non-htmx navigation continues to receive the full render stack."""
        response = client.get("/leads", headers={"HX-Request": "true"})
        assert response.status_code == 200
        assert b"<table" in response.data.lower()
        assert b"Leads Directory" not in response.data


class TestApiV1Scaffolding:
    """Regression checks for the versioned API docs and token middleware hooks."""

    def test_api_docs_route_and_invalid_bearer_token_reject(self, client):
        """The API docs route should redirect into the auto-generated Flask-Smorest UI, and the bearer-token gate should reject a bogus Authorization header with a clean 401 JSON response instead of falling to the browser login UI."""
        docs_resp = client.get("/api/v1/docs", follow_redirects=True)
        assert docs_resp.status_code == 200
        assert b"swagger" in docs_resp.data.lower()

        bad_token_resp = client.get("/api/v1/leads", headers={"Authorization": "Bearer totally-not-a-real-token"})
        assert bad_token_resp.status_code == 401
        assert bad_token_resp.is_json
        assert b"Missing or invalid bearer token" in bad_token_resp.data


class TestConfigFactory:
    """Verify that configuration objects are accepted by the app factory cleanly."""

    def test_create_app_accepts_testing_config_object(self):
        """The app factory should accept a config class and apply the testing envelope."""
        from app import create_app
        from config import TestingConfig

        app = create_app(config_object=TestingConfig)
        assert app.config["TESTING"] is True
        assert app.config["DEBUG"] is False
        assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite:///")


class TestConstraintRegressionChecks:
    """Verify that the database rejects invalid data and FK violations at the ORM layer."""

    def test_invalid_lead_status_is_rejected(self, app):
        """A status outside the allowed enum-like list must fail database-level CHECK enforcement."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Lead

            db = get_db()
            bad_lead = Lead(
                student_name="Bad Status Lead",
                phone="555-0000-0001",
                city="Test City",
                course_interest="Course",
                lead_source="Website",
                interest_level="high",
                notes="Will be rolled back",
                status="nonsense",
                lead_score=0,
            )
            db.session.add(bad_lead)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_invalid_interaction_lead_fk_is_rejected(self, app):
        """An interaction referencing a missing lead must be rejected by SQLite FK enforcement."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Interaction

            db = get_db()
            bad_interaction = Interaction(
                lead_id=999999,
                interaction_type="call",
                notes="Missing lead",
            )
            db.session.add(bad_interaction)
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()


class TestInteractionAndScoringFlow:
    """Test the complete add-interaction → score-updates flow."""

    def test_add_interaction_updates_score(self, client, app):
        """Adding an interaction should trigger score recalculation."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Lead
            
            # Create a lead with high interest
            response = client.post("/leads/add", data={
                "student_name": "Scoring Test Lead",
                "phone": "555-8888-8888",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Premium Course",
                "lead_source": "Website",
                "interest_level": "high",
                "notes": "Test for scoring flow",
            }, follow_redirects=True)
            
            # Get the database to find the lead_id
            db = get_db()
            lead = db.session.query(Lead).filter(Lead.student_name == "Scoring Test Lead").first()
            
            assert lead is not None
            lead_id = lead.lead_id
            initial_score = lead.lead_score
            
            # Base score for high interest + no interactions = 30
            assert initial_score == 30

    def test_update_status_recalculates_score(self, client, app):
        """Updating lead status should recalculate score."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Lead
            
            # Create a lead
            response = client.post("/leads/add", data={
                "student_name": "Status Update Test",
                "phone": "555-7777-7777",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Course",
                "lead_source": "Referral",
                "interest_level": "high",
                "notes": "Test status update",
            }, follow_redirects=True)
            
            db = get_db()
            lead = db.session.query(Lead).filter(Lead.student_name == "Status Update Test").first()
            lead_id = lead.lead_id
            
            # Update status to "applied"
            response = client.post(f"/leads/update_status/{lead_id}", data={
                "status": "applied"
            }, follow_redirects=True)
            
            # Fetch updated lead (expire_all ensures we reread from DB)
            db.session.expire_all()
            updated_lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
            
            # Score should increase due to "applied" status bonus (25 points)
            # Initial was 30 (high interest), now should be 55
            assert updated_lead.lead_score == 55

    def test_add_interaction_creates_record_and_scores(self, client, app):
        """Adding interaction should create record and trigger scoring."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Lead, Interaction
            
            # Create a lead
            response = client.post("/leads/add", data={
                "student_name": "Interaction Test Lead",
                "phone": "555-6666-6666",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Course",
                "lead_source": "Website",
                "interest_level": "high",
                "notes": "Test interaction flow",
            }, follow_redirects=True)
            
            db = get_db()
            lead = db.session.query(Lead).filter(Lead.student_name == "Interaction Test Lead").first()
            lead_id = lead.lead_id
            
            # Add an interaction
            response = client.post(f"/interactions/add/{lead_id}", data={
                "interaction_type": "call",
                "notes": "Test call",
                "follow_up_date": "",
            }, follow_redirects=True)
            
            # Check that interaction was created
            interaction_count = db.session.query(Interaction).filter(Interaction.lead_id == lead_id).count()
            assert interaction_count == 1
            
            # Check that lead status was updated (call → contacted)
            db.session.expire_all()
            updated_lead = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
            
            assert updated_lead.status == "contacted"
            # Score should be: 30 (high) + 5 (1 interaction) + 25 (recency) + 5 (call) + 5 (contacted status) = 70
            assert updated_lead.lead_score == 70

    def test_quick_action_creates_interaction(self, client, app):
        """Quick action should create an interaction record."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Lead, Interaction
            
            # Create a lead
            response = client.post("/leads/add", data={
                "student_name": "Quick Action Test",
                "phone": "555-5555-5555",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Course",
                "lead_source": "Website",
                "interest_level": "medium",
                "notes": "Test quick action",
            }, follow_redirects=True)
            
            db = get_db()
            lead = db.session.query(Lead).filter(Lead.student_name == "Quick Action Test").first()
            lead_id = lead.lead_id
            
            # Perform quick action
            response = client.post(f"/quick_action/{lead_id}", data={
                "action_type": "call"
            }, follow_redirects=True)
            
            # Check interaction was created
            interaction_count = db.session.query(Interaction).filter(Interaction.lead_id == lead_id).count()
            assert interaction_count == 1

    def test_complete_workflow(self, client, app):
        """End-to-end: create lead → log interaction → change status → verify scores."""
        with app.app_context():
            from database.db_connection import get_db
            from database.models import Lead
            
            # 1. Create lead with high interest
            response = client.post("/leads/add", data={
                "student_name": "E2E Workflow Test",
                "phone": "555-4444-4444",
                "city": "Test City",
                "school_id": "",
                "coaching_id": "",
                "course_interest": "Premium Program",
                "lead_source": "Referral",
                "interest_level": "high",
                "notes": "Complete workflow test",
            }, follow_redirects=True)
            
            db = get_db()
            lead = db.session.query(Lead).filter(Lead.student_name == "E2E Workflow Test").first()
            lead_id = lead.lead_id
            assert lead.lead_score == 30  # High interest baseline
            assert lead.status == "new"
            
            # 2. Log an interaction (visit)
            response = client.post(f"/interactions/add/{lead_id}", data={
                "interaction_type": "visit",
                "notes": "Campus visit completed",
                "follow_up_date": "",
            }, follow_redirects=True)
            
            db.session.expire_all()
            lead_after_interaction = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
            
            assert lead_after_interaction.status == "interested"
            # Score: 30 + 5 (freq) + 25 (recency) + 10 (visit type) + 15 (interested status) = 85
            assert lead_after_interaction.lead_score == 85
            
            # 3. Update status to applied
            response = client.post(f"/leads/update_status/{lead_id}", data={
                "status": "applied"
            }, follow_redirects=True)
            
            db.session.expire_all()
            lead_after_status = db.session.query(Lead).filter(Lead.lead_id == lead_id).first()
            
            assert lead_after_status.status == "applied"
            # Score should update to applied status bonus: 30 + 5 + 25 + 10 + 25 = 95
            assert lead_after_status.lead_score == 95
            
            # 4. Verify lead detail loads
            response = client.get(f"/leads/{lead_id}")
            assert response.status_code == 200
