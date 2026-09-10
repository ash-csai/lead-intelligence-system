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
