"""
Incident Intelligence Agent - LangGraph Node.
Converts unstructured citizen reports into validated incident entities.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.incident_intelligence.extractor import extract_incident_entities
from agents.incident_intelligence.duplicate_detector import check_for_duplicates


async def run_incident_intelligence(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Incident Intelligence Agent LangGraph node.

    Executes:
    1. Entity extraction from raw report text
    2. Duplicate detection via spatial proximity check
    3. State updates with extraction results and audit trail

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client (created if not provided)

    Returns:
        Updated state with extraction results and audit logs
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()
        close_client = True
    else:
        close_client = False

    try:
        # Extract raw report data
        raw_report = state.get("raw_report")
        if not raw_report:
            state["errors"] = state.get("errors", [])
            state["errors"].append("IncidentIntelligence: No raw_report found in state")
            return state

        report_text = raw_report.get("description", "")
        location = raw_report.get("location")
        district = raw_report.get("district", "")

        # Extract structured entities
        location_hint = f"{district}" if district else None
        extracted = await extract_incident_entities(report_text, location_hint)

        # Store extraction in state
        state["extraction"] = extracted.model_dump()

        # Check for duplicates if location coordinates available
        duplicate_info = None
        if location and "coordinates" in location:
            lng, lat = location["coordinates"]  # GeoJSON order: [lng, lat]
            duplicate_info = await check_for_duplicates(client, lat, lng, radius_m=200)

            if duplicate_info:
                state["duplicate_incidents"] = [duplicate_info]

        # Build audit trail entry
        audit_entry = {
            "agent": "IncidentIntelligenceAgent",
            "action": "extraction_complete",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": {
                "hazard_type": extracted.hazard_type.value,
                "people_affected": extracted.people_affected,
                "confidence": extracted.confidence_score,
                "is_ambiguous": extracted.is_ambiguous,
                "duplicate_detected": duplicate_info is not None
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
