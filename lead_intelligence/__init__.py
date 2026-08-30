"""
Lead Intelligence Package — Portable Scoring & Priority Logic

This package contains pure, data-driven scoring and priority evaluation logic
with ZERO external dependencies on:
  • Flask or any web framework
  • SQLite or any database
  • This specific database schema

All functions operate on plain Python dictionaries (lead data, interaction records).
No database connections needed.

Public API (all pure functions, zero side effects):
  • calculate_lead_score(lead, interactions) → int
  • evaluate_lead_priority(lead, interactions, last_action=None) → dict
  • HOT_LEAD_THRESHOLD, WARM_LEAD_THRESHOLD constants
"""

from .scoring import (
    HOT_LEAD_THRESHOLD,
    WARM_LEAD_THRESHOLD,
    calculate_lead_score,
)
from .priority import (
    build_priority_details,
    calculate_priority_score,
    build_priority_reasons,
    suggest_priority_action,
)

__all__ = [
    "HOT_LEAD_THRESHOLD",
    "WARM_LEAD_THRESHOLD",
    "calculate_lead_score",
    "build_priority_details",
    "calculate_priority_score",
    "build_priority_reasons",
    "suggest_priority_action",
]
