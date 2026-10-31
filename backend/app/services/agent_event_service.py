"""
Agent event logging service.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.agent_event import AgentEvent


async def log_agent_event(
    db: AsyncSession,
    agent_name: str,
    action_type: str,
    input_context: dict,
    output_decision: dict,
    incident_id: Optional[UUID] = None,
    confidence_score: Optional[float] = None,
    execution_time_ms: int = 0,
) -> AgentEvent:
    """
    Insert a row into agent_events table.

    Args:
        db: Database session
        agent_name: Agent name (e.g., 'DiscrepancyDetector')
        action_type: Action type (e.g., 'DISCREPANCY_DETECTED')
        input_context: Input context dict
        output_decision: Output decision dict
        incident_id: Optional incident UUID
        confidence_score: Optional confidence score (0.0-1.0)
        execution_time_ms: Execution time in milliseconds

    Returns:
        Created AgentEvent object
    """
    agent_event = AgentEvent(
        incident_id=incident_id,
        agent_name=agent_name,
        action_type=action_type,
        input_context=input_context,
        output_decision=output_decision,
        confidence_score=confidence_score,
        execution_time_ms=execution_time_ms
    )

    db.add(agent_event)
    await db.flush()

    return agent_event
