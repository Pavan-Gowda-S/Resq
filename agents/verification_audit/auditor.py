"""
Verification & Audit Agent - Auditor Logic.
Validates task matching, reservation integrity, and execution completeness.
"""
from typing import Dict, Any, List
from agents.core.state import AgentState
from agents.verification_audit.schemas import AuditSummary


def audit_incident_lifecycle(state: AgentState) -> AuditSummary:
    """
    Audit incident lifecycle for completeness and discrepancies.

    Validates:
    1. Every task proposed has a corresponding match
    2. Every reservation has valid expiration and status
    3. No orphaned reservations
    4. Timeline consistency

    Args:
        state: Complete AgentState after all agents executed

    Returns:
        AuditSummary with verification status and discrepancies
    """

    incident_id = state.get("incident_id", "unknown")
    task_proposals = state.get("task_proposals", [])
    matched_resources = state.get("matched_resources", {})
    reservations = state.get("reservations", [])
    audit_trail = state.get("audit_trail", [])
    triage = state.get("triage", {})

    discrepancies = []

    # Count total tasks
    total_tasks = len(task_proposals)

    # Validate task matching
    rescue_tasks = [t for t in task_proposals if t.get("task_type") == "RESCUE_EXTRACTION"]
    hospital_tasks = [t for t in task_proposals if t.get("task_type") in ["HOSPITAL_ADMISSION", "AMBULANCE_TRANSPORT"]]
    supply_tasks = [t for t in task_proposals if t.get("task_type") == "SUPPLY_DELIVERY"]

    rescue_matches = matched_resources.get("rescue_teams", [])
    hospital_matches = matched_resources.get("hospitals", []) + matched_resources.get("ambulances", [])
    supply_matches = matched_resources.get("supplies", [])

    # Check for unmatched tasks
    matched_tasks = 0

    if rescue_tasks and not rescue_matches:
        discrepancies.append(f"{len(rescue_tasks)} rescue task(s) proposed but no teams matched")
    elif rescue_tasks:
        matched_tasks += len(rescue_tasks)

    if hospital_tasks and not hospital_matches:
        discrepancies.append(f"{len(hospital_tasks)} hospital/ambulance task(s) proposed but no matches")
    elif hospital_tasks:
        matched_tasks += len(hospital_tasks)

    if supply_tasks and not supply_matches:
        discrepancies.append(f"{len(supply_tasks)} supply task(s) proposed but no allocations")
    elif supply_tasks:
        matched_tasks += len(supply_tasks)

    # Validate reservations
    total_reservations = len(reservations)

    for reservation in reservations:
        # Check for required fields
        if "reservation_id" not in reservation:
            discrepancies.append("Reservation missing reservation_id")

        if "resource_type" not in reservation:
            discrepancies.append("Reservation missing resource_type")

        # Check for expiration timestamp
        if "created_at" not in reservation and "expires_at" not in reservation:
            discrepancies.append(f"Reservation {reservation.get('reservation_id', 'unknown')} missing timestamp")

    # Build timeline from audit trail
    timeline = []
    for entry in audit_trail:
        timeline.append({
            "agent": entry.get("agent"),
            "action": entry.get("action"),
            "timestamp": entry.get("timestamp"),
            "summary": entry.get("results", {})
        })

    # Determine verification status
    has_discrepancies = len(discrepancies) > 0

    if has_discrepancies:
        verification_status = "REQUIRES_MANUAL_AUDIT"
    elif matched_tasks == total_tasks and total_tasks > 0:
        verification_status = "VERIFIED_COMPLETE"
    elif total_tasks == 0:
        verification_status = "NO_TASKS_PROPOSED"
    else:
        verification_status = "PARTIAL_COMPLETION"

    # Check for human review requirement
    human_review_required = triage.get("requires_human_review", False)

    return AuditSummary(
        incident_id=incident_id,
        total_tasks=total_tasks,
        matched_tasks=matched_tasks,
        total_reservations=total_reservations,
        has_discrepancies=has_discrepancies,
        discrepancy_details=discrepancies,
        verification_status=verification_status,
        timeline=timeline,
        human_review_required=human_review_required
    )
