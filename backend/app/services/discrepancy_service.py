"""
Discrepancy detection service for arrival confirmation mismatches.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import ResponseTask
from backend.app.services.agent_event_service import log_agent_event

# Threshold for discrepancy detection (15 minutes)
DISCREPANCY_THRESHOLD_MINUTES = 15


async def check_arrival_discrepancy(
    task_id: UUID,
    db: AsyncSession
) -> Optional[dict]:
    """
    Check if responder marked ON_SCENE but citizen hasn't confirmed within threshold.

    Returns discrepancy info if detected, None otherwise.

    Args:
        task_id: Task UUID to check
        db: Database session

    Returns:
        Discrepancy dict if found, None otherwise
    """
    # Get task
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return None

    # Only check tasks that are ON_SCENE with arrived_at timestamp
    if task.status != "ON_SCENE" or not task.arrived_at:
        return None

    # Check if citizen has confirmed
    if task.citizen_confirmed_arrival:
        return None

    # Calculate time since arrival
    now = datetime.now(timezone.utc)
    time_since_arrival = now - task.arrived_at

    # Check if threshold exceeded
    if time_since_arrival.total_seconds() < (DISCREPANCY_THRESHOLD_MINUTES * 60):
        return None

    # Discrepancy detected - log it using agent event service
    discrepancy_info = {
        "discrepancy_type": "UNCONFIRMED_ARRIVAL",
        "arrived_at": task.arrived_at.isoformat(),
        "minutes_since_arrival": int(time_since_arrival.total_seconds() / 60),
        "threshold_minutes": DISCREPANCY_THRESHOLD_MINUTES
    }

    # Log as AgentEvent
    await log_agent_event(
        db=db,
        agent_name="DiscrepancyDetector",
        action_type="DISCREPANCY_DETECTED",
        input_context={"task_id": str(task_id), "status": task.status},
        output_decision=discrepancy_info,
        incident_id=task.incident_id,
        execution_time_ms=0
    )

    return discrepancy_info
