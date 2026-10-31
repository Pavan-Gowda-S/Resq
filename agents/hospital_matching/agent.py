"""
Hospital & Medical Matching Agent - LangGraph Node.
Matches hospitals and ambulances to medical tasks and creates reservations.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.hospital_matching.matcher import match_hospital_and_transport
from shared.constants import TaskType


async def run_hospital_matching(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Hospital & Medical Matching Agent LangGraph node.

    Executes:
    1. Scans task proposals for HOSPITAL_ADMISSION and AMBULANCE_TRANSPORT tasks
    2. Matches hospitals with verified capacity
    3. Creates atomic bed reservations
    4. Matches ambulances for transport
    5. Records results in state
    6. Updates audit trail

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client (created if not provided)

    Returns:
        Updated state with hospital matches and reservations
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()
        close_client = True
    else:
        close_client = False

    try:
        # Get task proposals and triage
        task_proposals = state.get("task_proposals", [])
        triage = state.get("triage", {})

        if not task_proposals:
            return state

        # Filter medical tasks
        medical_tasks = [
            task for task in task_proposals
            if task.get("task_type") in [
                TaskType.HOSPITAL_ADMISSION.value,
                TaskType.AMBULANCE_TRANSPORT.value
            ]
        ]

        if not medical_tasks:
            return state

        # Initialize matched resources and reservations
        if "matched_resources" not in state:
            state["matched_resources"] = {}

        if "reservations" not in state:
            state["reservations"] = []

        hospital_matches = []
        ambulance_matches = []

        # Match hospitals and ambulances for each medical task
        for task in medical_tasks:
            match_result = await match_hospital_and_transport(task, triage, client)

            result_dict = match_result.model_dump()

            if match_result.hospital:
                hospital_matches.append({
                    "task_id": match_result.task_id,
                    "hospital": result_dict["hospital"]
                })

            if match_result.ambulance:
                ambulance_matches.append({
                    "task_id": match_result.task_id,
                    "ambulance": result_dict["ambulance"]
                })

            if match_result.reservation_id:
                state["reservations"].append({
                    "reservation_id": match_result.reservation_id,
                    "task_id": match_result.task_id,
                    "resource_type": match_result.hospital.matched_bed_type if match_result.hospital else "UNKNOWN",
                    "organization_id": match_result.hospital.organization_id if match_result.hospital else "UNKNOWN",
                    "created_at": datetime.utcnow().isoformat() + "Z"
                })

        # Store matches in state
        state["matched_resources"]["hospitals"] = hospital_matches
        state["matched_resources"]["ambulances"] = ambulance_matches

        # Build audit trail entry
        audit_entry = {
            "agent": "HospitalMatchingAgent",
            "action": "hospital_and_transport_matching_complete",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": {
                "medical_tasks_count": len(medical_tasks),
                "hospitals_matched": len(hospital_matches),
                "ambulances_matched": len(ambulance_matches),
                "reservations_created": len([r for r in state["reservations"] if "reservation_id" in r])
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
