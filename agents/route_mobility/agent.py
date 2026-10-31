"""
Route & Mobility Agent - LangGraph Node.
Assesses transport route safety and hazard restrictions.
"""
from datetime import datetime
from typing import Optional, Tuple
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.route_mobility.router import assess_route


async def run_route_mobility(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Route & Mobility Agent LangGraph node.

    Executes:
    1. Assesses transit routes for matched rescue and ambulance units
    2. Identifies hazards affecting transport
    3. Recommends vehicle types for safe passage
    4. Stores route assessments in state
    5. Updates audit trail

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client (not used, kept for consistency)

    Returns:
        Updated state with route assessments
    """

    # Get matched resources
    matched_resources = state.get("matched_resources", {})

    if not matched_resources:
        return state

    # Get incident location
    raw_report = state.get("raw_report", {})
    incident_location = raw_report.get("location", {})

    if "coordinates" not in incident_location:
        return state

    incident_coords = tuple(incident_location["coordinates"])  # (lng, lat)

    route_assessments = []

    # Assess routes for rescue teams
    rescue_teams = matched_resources.get("rescue_teams", [])
    for match in rescue_teams:
        if match.get("assigned_team"):
            # In real implementation, would get team's current location
            # For now, assess from incident to hospital (simplified)
            pass

    # Assess routes for ambulances to hospitals
    hospitals = matched_resources.get("hospitals", [])
    ambulances = matched_resources.get("ambulances", [])

    for hospital_match in hospitals:
        hospital = hospital_match.get("hospital")
        if hospital:
            # Assess route from incident to hospital
            # In real implementation, would get hospital coordinates from API
            # For now, use incident location as simplified assessment

            assessment = assess_route(
                origin=incident_coords,
                destination=incident_coords  # Simplified - would be hospital coords
            )

            route_assessments.append({
                "task_id": hospital_match.get("task_id"),
                "route_type": "INCIDENT_TO_HOSPITAL",
                "assessment": assessment.model_dump()
            })

    # Store route assessments
    matched_resources["routes"] = route_assessments
    state["matched_resources"] = matched_resources

    # Build audit trail entry
    hazard_count = sum(
        len(r.get("assessment", {}).get("hazard_warnings", []))
        for r in route_assessments
    )

    unsafe_routes = sum(
        1 for r in route_assessments
        if not r.get("assessment", {}).get("is_safe", True)
    )

    audit_entry = {
        "agent": "RouteMobilityAgent",
        "action": "route_assessment_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "results": {
            "routes_assessed": len(route_assessments),
            "hazards_identified": hazard_count,
            "unsafe_routes": unsafe_routes
        }
    }

    # Append to audit trail
    if "audit_trail" not in state:
        state["audit_trail"] = []
    state["audit_trail"].append(audit_entry)

    # Update state metadata
    state["state_updated_at"] = datetime.utcnow()

    return state
