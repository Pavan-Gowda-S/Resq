"""
Risk & Decision Agent - LangGraph Node.
Deterministic triage assessment and multi-pathway task proposal generation.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.incident_intelligence.schemas import ExtractedEntities
from agents.risk_decision.triage_rules import evaluate_incident_risk
from agents.risk_decision.pathway_generator import generate_task_pathways
from agents.risk_decision.schemas import RiskDecisionOutput
from shared.schemas import TaskProposalsPayload, ResponseTaskProposal, GeoPoint


async def run_risk_decision(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Risk & Decision Agent LangGraph node.

    Executes:
    1. Deterministic triage risk assessment
    2. Multi-pathway task proposal generation
    3. Task submission via ResqApiClient
    4. State updates with triage results and audit trail

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client (created if not provided)

    Returns:
        Updated state with triage results, task proposals, and audit logs
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()
        close_client = True
    else:
        close_client = False

    try:
        # Verify extraction exists
        extraction_data = state.get("extraction")
        if not extraction_data:
            state["errors"] = state.get("errors", [])
            state["errors"].append("RiskDecision: No extraction found in state")
            return state

        # Reconstruct ExtractedEntities from state
        extraction = ExtractedEntities(**extraction_data)

        # Get incident location
        raw_report = state.get("raw_report", {})
        location = raw_report.get("location")

        if not location or "coordinates" not in location:
            state["errors"] = state.get("errors", [])
            state["errors"].append("RiskDecision: No location coordinates found")
            return state

        coordinates = location["coordinates"]  # [lng, lat]

        # Execute deterministic triage assessment
        triage = evaluate_incident_risk(extraction)

        # Generate multi-pathway task proposals
        proposals = generate_task_pathways(extraction, triage, coordinates)

        # Store triage in state
        state["triage"] = triage.model_dump()

        # Prepare task proposals for backend API
        incident_id = state.get("incident_id")

        if incident_id and len(proposals) > 0:
            # Convert proposals to API payload format
            api_proposals = [
                ResponseTaskProposal(
                    task_type=p.task_type,
                    priority=p.priority,
                    target_location=p.target_location,
                    instructions=p.instructions,
                    parent_task_id=p.parent_task_id
                )
                for p in proposals
            ]

            payload = TaskProposalsPayload(proposals=api_proposals)

            # Submit tasks to backend
            result = await client.propose_tasks(incident_id, payload)

            # Store created tasks in state
            state["task_proposals"] = [p.model_dump() for p in proposals]
            state["created_tasks"] = result.get("created_tasks", [])
        else:
            # No incident ID yet or no proposals generated
            state["task_proposals"] = [p.model_dump() for p in proposals]

        # Build audit trail entry
        audit_entry = {
            "agent": "RiskDecisionAgent",
            "action": "triage_and_task_proposal_complete",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": {
                "priority": triage.priority.value,
                "priority_score": triage.priority_score,
                "life_threat_detected": triage.life_threat_detected,
                "requires_human_review": triage.requires_human_review,
                "task_count": len(proposals),
                "task_types": [p.task_type.value for p in proposals]
            }
        }

        # Append to audit trail
        if "audit_trail" not in state:
            state["audit_trail"] = []
        state["audit_trail"].append(audit_entry)

        # Update state metadata
        state["state_updated_at"] = datetime.utcnow()

        return state

    finally:
        # Clean up client if we created it
        if close_client:
            await client.close()
