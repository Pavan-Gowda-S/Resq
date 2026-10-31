"""
Verification & Audit Agent - LangGraph Node.
Final verification and immutable audit seal for incident lifecycle.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.verification_audit.auditor import audit_incident_lifecycle


async def run_verification_audit(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Verification & Audit Agent LangGraph node.

    Executes:
    1. Validates all proposed tasks have corresponding matches
    2. Verifies reservation integrity (expiration, status)
    3. Checks for orphaned reservations
    4. Compiles execution timeline from audit trail
    5. Generates immutable audit summary
    6. Appends final seal to audit trail

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client (not used, kept for consistency)

    Returns:
        Updated state with audit summary and final seal
    """

    # Append final seal to audit trail
    final_seal = {
        "agent": "VerificationAuditAgent",
        "action": "lifecycle_audit_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "results": {
            "status": "SEALED"
        }
    }

    if "audit_trail" not in state:
        state["audit_trail"] = []
    state["audit_trail"].append(final_seal)

    # Generate audit summary
    audit_summary = audit_incident_lifecycle(state)

    # Store audit summary in state
    state["audit_summary"] = {
        "incident_id": audit_summary.incident_id,
        "total_tasks": audit_summary.total_tasks,
        "matched_tasks": audit_summary.matched_tasks,
        "total_reservations": audit_summary.total_reservations,
        "has_discrepancies": audit_summary.has_discrepancies,
        "discrepancy_details": audit_summary.discrepancy_details,
        "verification_status": audit_summary.verification_status,
        "timeline": audit_summary.timeline,
        "human_review_required": audit_summary.human_review_required
    }

    # Update state metadata
    state["state_updated_at"] = datetime.utcnow()

    return state
