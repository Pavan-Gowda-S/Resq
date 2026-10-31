"""
RESQ LangGraph Global State Schema.
Defines the shared state structure passed between agent nodes.
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class AgentState(TypedDict, total=False):
    """
    LangGraph state dictionary for RESQ multi-agent coordination.
    Each field is optional to allow incremental state building across agent nodes.
    """

    # Incident Identity
    incident_id: Optional[str]
    tracking_token: Optional[str]
    incident_number: Optional[str]

    # Raw Input
    raw_report: Optional[Dict[str, Any]]

    # Incident Intelligence Agent Output
    extraction: Optional[Dict[str, Any]]  # hazard_type, victim_count, medical_conditions, trapped_status
    duplicate_incidents: Optional[List[Dict[str, Any]]]

    # Risk & Decision Agent Output
    triage: Optional[Dict[str, Any]]  # priority, confidence, rationale
    task_proposals: Optional[List[Dict[str, Any]]]  # linked response tasks

    # Rescue Matching Agent Output
    matched_rescue_teams: Optional[List[Dict[str, Any]]]

    # Hospital Matching Agent Output
    matched_hospitals: Optional[List[Dict[str, Any]]]
    matched_ambulances: Optional[List[Dict[str, Any]]]

    # Resource Marketplace Agent Output
    matched_resources: Optional[Dict[str, Any]]  # supplies, blood units, etc.

    # Reservation & Allocation Results
    reservations: Optional[List[Dict[str, Any]]]  # bed/supply atomic locks

    # Offline & Sync Events
    offline_events: Optional[List[Dict[str, Any]]]

    # Audit & Verification Trail
    audit_trail: Optional[List[Dict[str, Any]]]  # timestamped agent execution logs
    audit_summary: Optional[Dict[str, Any]]  # final verification audit summary

    # Human-in-the-Loop Checkpoints
    human_review_required: Optional[bool]
    created_tasks: Optional[List[Dict[str, Any]]]

    # Error Accumulation
    errors: Optional[List[str]]

    # Metadata
    state_created_at: Optional[datetime]
    state_updated_at: Optional[datetime]
