"""
VerdictFlow — Band SDK Event Types

Structured event types for inter-agent coordination in Band case rooms.
Each event signals a stage transition in the analysis pipeline.
"""

from enum import Enum
from typing import Any


class BandEventType(str, Enum):
    """Event types broadcast through Band case rooms."""

    # ── Pipeline Stage Events ──
    INTAKE_COMPLETE = "intake_complete"
    CLAUSE_ANALYSIS_COMPLETE = "clause_analysis_complete"
    RED_TEAM_COMPLETE = "red_team_complete"
    FINANCIAL_RISK_COMPLETE = "financial_risk_complete"
    COMPLIANCE_COMPLETE = "compliance_complete"
    REDLINE_COMPLETE = "redline_complete"

    # ── Human Gate Events ──
    HUMAN_GATE_REQUESTED = "human_gate_requested"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"

    # ── Case Lifecycle Events ──
    CASE_CREATED = "case_created"
    CASE_FINALIZED = "case_finalized"
    CASE_ERROR = "case_error"

    # ── Agent Status Events ──
    AGENT_STARTED = "agent_started"
    AGENT_PROGRESS = "agent_progress"
    AGENT_FINDING = "agent_finding"
    AGENT_ERROR = "agent_error"


def make_event_payload(
    event_type: BandEventType,
    case_id: str,
    agent_name: str = "",
    **kwargs: Any,
) -> dict:
    """
    Create a standardized event payload for Band room broadcasting.

    Args:
        event_type: The type of event
        case_id: The case this event belongs to
        agent_name: The agent emitting the event
        **kwargs: Additional event-specific data

    Returns:
        Standardized event payload dict
    """
    return {
        "event_type": event_type.value,
        "case_id": case_id,
        "agent_name": agent_name,
        **kwargs,
    }
