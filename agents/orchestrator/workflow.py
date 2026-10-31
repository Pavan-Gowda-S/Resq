"""
LangGraph Orchestrator - Workflow Execution Pipeline.
Complete incident lifecycle orchestration from raw report to audit seal.
"""
from typing import Dict, Any, Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.orchestrator.graph import build_orchestrator_graph


async def process_incident_lifecycle(
    raw_report: Dict[str, Any],
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Process complete incident lifecycle through multi-agent orchestration.

    Executes the full LangGraph workflow:
    1. Reports incident to backend (obtains canonical incident_id)
    2. Initializes AgentState with raw report
    3. Runs unified StateGraph through all agents
    4. Returns finalized state with audit summary

    Args:
        raw_report: Raw incident report dictionary with:
            - description: str
            - district: str
            - location: GeoPoint dict with coordinates
            - reporter_name: Optional[str]
            - reporter_phone: Optional[str]
        client: Optional RESQ API client (creates new if not provided)

    Returns:
        Final AgentState with complete execution history and audit seal
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()

    try:
        # Report incident to backend to obtain canonical incident_id
        incident_response = await client.report_incident(raw_report)
        incident_id = incident_response.get("incident_id", "unknown")

        # Initialize AgentState
        initial_state: AgentState = {
            "incident_id": incident_id,
            "raw_report": {
                "description": raw_report.get("description", ""),
                "district": raw_report.get("district", ""),
                "location": raw_report.get("location", {}),
                "reporter_name": raw_report.get("reporter_name"),
                "reporter_phone": raw_report.get("reporter_phone")
            }
        }

        # Build and compile orchestrator graph
        compiled_graph = build_orchestrator_graph(client)

        # Execute workflow
        final_state = await compiled_graph.ainvoke(initial_state)

        return final_state

    finally:
        # Close client if we created it
        if client is not None:
            await client.close()


async def process_incident_lifecycle_without_backend(
    raw_report: Dict[str, Any],
    incident_id: str = "test-incident",
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Process incident lifecycle without backend reporting (for testing).

    Skips the initial backend report and directly initializes state.
    Useful for end-to-end tests where incident_id is predetermined.

    Args:
        raw_report: Raw incident report dictionary
        incident_id: Predetermined incident ID
        client: Optional RESQ API client

    Returns:
        Final AgentState with complete execution history
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()

    try:
        # Initialize AgentState directly
        initial_state: AgentState = {
            "incident_id": incident_id,
            "raw_report": {
                "description": raw_report.get("description", ""),
                "district": raw_report.get("district", ""),
                "location": raw_report.get("location", {}),
                "reporter_name": raw_report.get("reporter_name"),
                "reporter_phone": raw_report.get("reporter_phone")
            }
        }

        # Build and compile orchestrator graph
        compiled_graph = build_orchestrator_graph(client)

        # Execute workflow
        final_state = await compiled_graph.ainvoke(initial_state)

        return final_state

    finally:
        # Close client if we created it
        if client is not None:
            await client.close()
