"""Test suite for lead_intelligence package (pure scoring & priority logic)."""

from datetime import datetime, timedelta
import pytest

from lead_intelligence.scoring import calculate_lead_score, HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD
from lead_intelligence.priority import (
    calculate_priority_score,
    build_priority_reasons,
    suggest_priority_action,
    build_priority_details,
)


class TestCalculateLeadScore:
    """Test calculate_lead_score() across interest_level/status/interaction combinations."""

    def test_high_interest_no_interactions(self):
        """High interest with no interactions should give base score."""
        lead = {"interest_level": "high", "status": "new"}
        interactions = []
        score = calculate_lead_score(lead, interactions)
        assert score == 30  # 30 base for high interest

    def test_medium_interest_no_interactions(self):
        """Medium interest with no interactions should give base score."""
        lead = {"interest_level": "medium", "status": "new"}
        interactions = []
        score = calculate_lead_score(lead, interactions)
        assert score == 20  # 20 base for medium interest

    def test_low_interest_no_interactions(self):
        """Low interest with no interactions should give base score."""
        lead = {"interest_level": "low", "status": "new"}
        interactions = []
        score = calculate_lead_score(lead, interactions)
        assert score == 10  # 10 base for low interest

    def test_interaction_frequency_scoring(self):
        """Each interaction adds 5 points."""
        lead = {"interest_level": "high", "status": "new"}
        now = datetime.now()
        interactions = [
            {"interaction_type": "call", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")},
            {"interaction_type": "call", "created_at": (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")},
            {"interaction_type": "call", "created_at": (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")},
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 (high interest) + 15 (3 interactions * 5) + 25 (recency bonus for most recent at 1 day) + 15 (3 calls * 5) = 85
        assert score == 85

    def test_recency_boost_within_2_days(self):
        """Recent interaction (0-2 days ago) should add 25 points."""
        now = datetime.now()
        lead = {"interest_level": "high", "status": "new"}
        interactions = [
            {"interaction_type": "call", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")}
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 (base) + 5 (1 interaction) + 25 (recency) + 5 (call type) = 65
        assert score == 65

    def test_recency_boost_within_7_days(self):
        """Older but recent interaction (3-7 days ago) should add 15 points."""
        now = datetime.now()
        lead = {"interest_level": "high", "status": "new"}
        interactions = [
            {"interaction_type": "call", "created_at": (now - timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")}
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 (base) + 5 (1 interaction) + 15 (recency 3-7 days) + 5 (call type) = 55
        assert score == 55

    def test_recency_penalty_cold_lead(self):
        """Old interaction (>14 days) should subtract 10 points."""
        now = datetime.now()
        lead = {"interest_level": "high", "status": "new"}
        interactions = [
            {"interaction_type": "call", "created_at": (now - timedelta(days=20)).strftime("%Y-%m-%d %H:%M:%S")}
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 (base) + 5 (1 interaction) - 10 (cold lead) + 5 (call type) = 30
        assert score == 30

    def test_interaction_type_application(self):
        """Application interaction adds 20 points."""
        now = datetime.now()
        lead = {"interest_level": "high", "status": "new"}
        interactions = [
            {"interaction_type": "application", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")}
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 + 5 + 25 + 20 = 80
        assert score == 80

    def test_interaction_type_visit(self):
        """Visit interaction adds 10 points."""
        now = datetime.now()
        lead = {"interest_level": "high", "status": "new"}
        interactions = [
            {"interaction_type": "visit", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")}
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 + 5 + 25 + 10 = 70
        assert score == 70

    def test_interaction_type_call(self):
        """Call interaction adds 5 points."""
        now = datetime.now()
        lead = {"interest_level": "high", "status": "new"}
        interactions = [
            {"interaction_type": "call", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")}
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 + 5 + 25 + 5 = 65
        assert score == 65

    def test_status_applied(self):
        """Applied status adds 25 points."""
        lead = {"interest_level": "high", "status": "applied"}
        interactions = []
        score = calculate_lead_score(lead, interactions)
        assert score == 55  # 30 + 25

    def test_status_interested(self):
        """Interested status adds 15 points."""
        lead = {"interest_level": "high", "status": "interested"}
        interactions = []
        score = calculate_lead_score(lead, interactions)
        assert score == 45  # 30 + 15

    def test_status_contacted(self):
        """Contacted status adds 5 points."""
        lead = {"interest_level": "high", "status": "contacted"}
        interactions = []
        score = calculate_lead_score(lead, interactions)
        assert score == 35  # 30 + 5

    def test_combined_scoring(self):
        """Comprehensive test with multiple factors."""
        now = datetime.now()
        lead = {
            "interest_level": "high",
            "status": "applied",
        }
        interactions = [
            {"interaction_type": "application", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")},
            {"interaction_type": "visit", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")},
            {"interaction_type": "call", "created_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")},
        ]
        score = calculate_lead_score(lead, interactions)
        # 30 (high interest)
        # + 15 (3 interactions * 5)
        # + 25 (recency bonus, most recent is 1 day ago)
        # + 20 (application) + 10 (visit) + 5 (call)
        # + 25 (applied status)
        # = 130
        assert score == 130

    def test_hot_lead_threshold(self):
        """Verify HOT_LEAD_THRESHOLD is accessible."""
        assert HOT_LEAD_THRESHOLD == 70

    def test_warm_lead_threshold(self):
        """Verify WARM_LEAD_THRESHOLD is accessible."""
        assert WARM_LEAD_THRESHOLD == 40


class TestCalculatePriorityScore:
    """Test calculate_priority_score() for urgency calculation."""

    def test_overdue_followup(self):
        """Overdue (days_diff < 0) should have high urgency."""
        urgency_score = calculate_priority_score(lead_score=50, days_diff=-1)
        # days_diff <= 0 gives urgency_score = 50
        priority = 50 + 50
        assert urgency_score == priority
        assert urgency_score == 100

    def test_today_followup(self):
        """Today follow-up (days_diff == 0) should have high urgency."""
        urgency_score = calculate_priority_score(lead_score=50, days_diff=0)
        priority = 50 + 50
        assert urgency_score == priority
        assert urgency_score == 100

    def test_near_term_followup(self):
        """1-2 days away should have medium urgency."""
        urgency_score = calculate_priority_score(lead_score=50, days_diff=1)
        # days_diff 1-2 gives urgency_score = 30
        priority = 30 + 50
        assert urgency_score == priority
        assert urgency_score == 80

    def test_far_term_followup(self):
        """>2 days away should have low urgency."""
        urgency_score = calculate_priority_score(lead_score=50, days_diff=7)
        # days_diff > 2 gives urgency_score = 10
        priority = 10 + 50
        assert urgency_score == priority
        assert urgency_score == 60

    def test_with_hot_lead(self):
        """Hot lead score should increase priority."""
        score_cold = calculate_priority_score(lead_score=30, days_diff=7)
        score_hot = calculate_priority_score(lead_score=80, days_diff=7)
        assert score_hot > score_cold

    def test_with_zero_lead_score(self):
        """Should handle None/zero lead score gracefully."""
        urgency_score = calculate_priority_score(lead_score=0, days_diff=0)
        assert urgency_score == 50  # Just the urgency component


class TestBuildPriorityReasons:
    """Test build_priority_reasons() for reason generation."""

    def test_overdue_reason(self):
        """Overdue should include 'Overdue follow-up'."""
        reasons = build_priority_reasons(days_diff=-1, lead_score=50)
        assert "Overdue follow-up" in reasons

    def test_today_reason(self):
        """Today should include 'Follow-up today'."""
        reasons = build_priority_reasons(days_diff=0, lead_score=50)
        assert "Follow-up today" in reasons

    def test_hot_lead_reason(self):
        """Hot lead should include 'High-value lead'."""
        reasons = build_priority_reasons(days_diff=5, lead_score=80)
        assert "High-value lead" in reasons

    def test_cold_lead_reason(self):
        """Cold lead should include 'Low engagement'."""
        reasons = build_priority_reasons(days_diff=5, lead_score=30)
        assert "Low engagement" in reasons

    def test_warm_lead_no_low_engagement(self):
        """Warm lead should not be marked as low engagement."""
        reasons = build_priority_reasons(days_diff=5, lead_score=50)
        assert "Low engagement" not in reasons

    def test_multiple_reasons(self):
        """Should combine multiple applicable reasons."""
        reasons = build_priority_reasons(days_diff=-1, lead_score=80)
        # Should have both "Overdue follow-up" and "High-value lead"
        assert "Overdue follow-up" in reasons
        assert "High-value lead" in reasons


class TestSuggestPriorityAction:
    """Test suggest_priority_action() for action recommendations."""

    def test_overdue_action(self):
        """Overdue should suggest 'Call immediately'."""
        action = suggest_priority_action(days_diff=-1, lead_score=50)
        assert action == "Call immediately"

    def test_today_action(self):
        """Today should suggest 'Call immediately'."""
        action = suggest_priority_action(days_diff=0, lead_score=50)
        assert action == "Call immediately"

    def test_hot_lead_action(self):
        """Hot lead should suggest 'Push for application'."""
        action = suggest_priority_action(days_diff=5, lead_score=80)
        assert action == "Push for application"

    def test_warm_lead_action(self):
        """Warm lead should suggest WhatsApp/Message follow-up."""
        action = suggest_priority_action(days_diff=5, lead_score=50)
        assert action == "Follow-up (WhatsApp/Message)"

    def test_cold_lead_action(self):
        """Cold lead should suggest slow nurture."""
        action = suggest_priority_action(days_diff=5, lead_score=30)
        assert action == "Low priority — nurture slowly"

    def test_zero_lead_score(self):
        """Should handle zero/None lead score gracefully."""
        action = suggest_priority_action(days_diff=5, lead_score=0)
        assert action == "Low priority — nurture slowly"


class TestBuildPriorityDetails:
    """Test build_priority_details() integration function."""

    def test_basic_priority_details(self):
        """Should build complete priority details dict."""
        today = datetime.now().date()
        lead = {
            "lead_id": 1,
            "student_name": "Alice",
            "lead_score": 75,
            "next_followup": (today + timedelta(days=1)).strftime("%Y-%m-%d"),
        }
        
        details = build_priority_details(lead, today=today)
        
        assert details["lead_id"] == 1
        assert details["student_name"] == "Alice"
        # For days_diff=1: urgency_score=30, total priority = 30 + 75 = 105
        assert details["priority_score"] == 105
        assert details["days_diff"] == 1
        assert "reasons" in details
        assert "suggestion" in details

    def test_overdue_priority_details(self):
        """Overdue lead should be marked urgent."""
        today = datetime.now().date()
        lead = {
            "lead_id": 2,
            "student_name": "Bob",
            "lead_score": 75,
            "next_followup": (today - timedelta(days=2)).strftime("%Y-%m-%d"),
        }
        
        details = build_priority_details(lead, today=today)
        
        assert details["days_diff"] == -2
        assert details["priority_score"] == 125  # 50 urgency + 75 lead_score
        assert "Overdue follow-up" in details["reasons"]
        assert details["suggestion"] == "Call immediately"

    def test_with_last_action(self):
        """Should include last_action when provided."""
        today = datetime.now().date()
        lead = {
            "lead_id": 3,
            "student_name": "Charlie",
            "lead_score": 60,
            "next_followup": today.strftime("%Y-%m-%d"),
        }
        
        details = build_priority_details(lead, last_action="call", today=today)
        
        assert details["last_action"] == "call"

    def test_default_today_parameter(self):
        """Should use current date if today not provided."""
        lead = {
            "lead_id": 4,
            "student_name": "Diana",
            "lead_score": 50,
            "next_followup": datetime.now().date().strftime("%Y-%m-%d"),
        }
        
        details = build_priority_details(lead)
        
        assert "priority_score" in details
        assert details["days_diff"] == 0
