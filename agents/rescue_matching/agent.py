"""
Rescue Matching Agent - LangGraph Node.
Matches rescue teams to extraction tasks and updates state.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.rescue_matching.matcher import match_rescue_teams
from shared.constants import TaskType


async def run_rescue_matching(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Rescue Matching Agent LangGraph node.

    Executes:
    1. Scans task proposals for RESCUE_EXTRACTION tasks
    2. Matches available rescue teams
    3. Records recommendations in state
    4. Updates audit trail

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client (created if not provided)

    Returns:
        Updated state with rescue team recommendations
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()
        close_client = True
    else:
        close_client = False

    try:
        # Get task proposals
        task_proposals = state.get("task_proposals", [])

        if not task_proposals:
            # No tasks to match
            return state

        # Filter rescue extraction tasks
        rescue_tasks = [
            task for task in task_proposals
            if task.get("task_type") == TaskType.RESCUE_EXTRACTION.value
        ]

        if not rescue_tasks:
            # No rescue tasks
            return state

        # Initialize matched resources
        if "matched_resources" not in state:
            state["matched_resources"] = {}

        rescue_matches = []

        # Match rescue teams for each extraction task
        for task in rescue_tasks:
            match_result = await match_rescue_teams(task, client)
            rescue_matches.append(match_result.model_dump())

        # Store rescue team matches in state
        state["matched_resources"]["rescue_teams"] = rescue_matches

        # Build audit trail entry
        assigned_count = sum(
            1 for match in rescue_matches
            if match.get("assigned_team") is not None
        )

        audit_entry = {
            "agent": "RescueMatchingAgent",
            "action": "rescue_team_matching_complete",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "results": {
                "rescue_tasks_count": len(rescue_tasks),
                "teams_matched": assigned_count,
                "total_recommendations": sum(
                    len(match.get("recommended_teams", []))
                    for match in rescue_matches
                )
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
