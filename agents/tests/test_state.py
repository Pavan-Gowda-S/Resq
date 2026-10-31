"""
Test cases for LangGraph state schema.
"""
import pytest
from datetime import datetime
from agents.core.state import AgentState


def test_agent_state_initialization():
    """Verify AgentState can be instantiated with basic fields."""
    state: AgentState = {
        "incident_id": "test-incident-123",
        "raw_report": {"description": "Test emergency"},
        "errors": []
    }

    assert state["incident_id"] == "test-incident-123"
    assert state["raw_report"]["description"] == "Test emergency"
    assert state["errors"] == []


def test_agent_state_incremental_build():
    """Verify state can be built incrementally across agent nodes."""
    state: AgentState = {}

    # Incident Intelligence Agent populates extraction
    state["incident_id"] = "inc-001"
    state["extraction"] = {
        "hazard_type": "FLOOD",
        "victim_count": 4,
        "trapped": True
    }

    # Risk & Decision Agent populates triage
    state["triage"] = {
        "priority": "CRITICAL",
        "confidence": 0.92,
        "rationale": "Multiple trapped victims with flooding hazard"
    }

    # Task proposals
    state["task_proposals"] = [
        {"task_type": "RESCUE_EXTRACTION", "priority": "CRITICAL"},
        {"task_type": "HOSPITAL_ADMISSION", "priority": "HIGH"}
    ]

    assert len(state["task_proposals"]) == 2
    assert state["triage"]["priority"] == "CRITICAL"


def test_agent_state_optional_fields():
    """Verify all fields are optional (total=False)."""
    # Empty state should be valid
    state: AgentState = {}

    # Can add any subset of fields
    state["incident_id"] = "inc-002"
    assert "extraction" not in state
    assert "triage" not in state

    # This should not raise any TypeErrors
    assert isinstance(state, dict)


def test_agent_state_audit_trail():
    """Verify audit trail accumulation."""
    state: AgentState = {
        "incident_id": "inc-003",
        "audit_trail": []
    }

    # Add audit entries
    state["audit_trail"].append({
        "agent": "IncidentIntelligence",
        "action": "extraction_complete",
        "timestamp": datetime.utcnow().isoformat()
    })

    state["audit_trail"].append({
        "agent": "RiskDecision",
        "action": "triage_complete",
        "timestamp": datetime.utcnow().isoformat()
    })

    assert len(state["audit_trail"]) == 2
    assert state["audit_trail"][0]["agent"] == "IncidentIntelligence"


def test_agent_state_error_accumulation():
    """Verify error accumulation pattern."""
    state: AgentState = {
        "incident_id": "inc-004",
        "errors": []
    }

    # Simulate agent errors
    state["errors"].append("Hospital matching: No ICU beds available within 50km")
    state["errors"].append("Route validation: Road closure detected on primary route")

    assert len(state["errors"]) == 2
    assert "No ICU beds" in state["errors"][0]
