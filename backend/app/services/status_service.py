"""
Status service: Status transition tracking and event logging.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import StatusEvent


async def record_status_change(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    previous_status: Optional[str],
    new_status: str,
    triggered_by_user_id: Optional[UUID] = None,
    payload: dict = None
) -> StatusEvent:
    """
    Record a status change event in the immutable audit ledger.

    Args:
        db: Database session
        entity_type: Type of entity (e.g., 'INCIDENT', 'TASK', 'RESOURCE')
        entity_id: UUID of the entity
        previous_status: Previous status (None for initial status)
        new_status: New status
        triggered_by_user_id: User who triggered the change (None for system/public)
        payload: Additional context as JSON

    Returns:
        Created StatusEvent object
    """
    if payload is None:
        payload = {}

    status_event = StatusEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        previous_status=previous_status,
        new_status=new_status,
        triggered_by_user_id=triggered_by_user_id,
        payload=payload,
    )

    db.add(status_event)
    return status_event


async def update_incident_status(
    db: AsyncSession,
    incident,
    new_status: str,
    triggered_by_user_id: Optional[UUID] = None,
    notes: Optional[str] = None
):
    """
    Update incident status and record the change.

    Args:
        db: Database session
        incident: Incident object to update
        new_status: New status value
        triggered_by_user_id: User who triggered the change
        notes: Optional notes about the status change
    """
    previous_status = incident.status
    incident.status = new_status

    # Record closed timestamp if moving to CLOSED status
    if new_status == "CLOSED" and incident.closed_at is None:
        incident.closed_at = datetime.now(timezone.utc)

    # Record status change event
    payload = {}
    if notes:
        payload["notes"] = notes

    await record_status_change(
        db=db,
        entity_type="INCIDENT",
        entity_id=incident.id,
        previous_status=previous_status,
        new_status=new_status,
        triggered_by_user_id=triggered_by_user_id,
        payload=payload
    )

    # Publish to Redis (non-blocking)
    try:
        from backend.app.services.pubsub_service import publish_incident_update
        await publish_incident_update(
            str(incident.id),
            {
                "event": "STATUS_CHANGED",
                "entity_type": "INCIDENT",
                "entity_id": str(incident.id),
                "new_status": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    except Exception as e:
        print(f"⚠ Failed to publish incident update: {e}")


async def update_task_status(
    db: AsyncSession,
    task,
    new_status: str,
    triggered_by_user_id: Optional[UUID] = None,
    notes: Optional[str] = None
):
    """
    Update task status and record the change.

    Args:
        db: Database session
        task: ResponseTask object to update
        new_status: New status value
        triggered_by_user_id: User who triggered the change
        notes: Optional notes about the status change
    """
    previous_status = task.status
    task.status = new_status

    # Update task timestamps based on status
    now = datetime.now(timezone.utc)

    if new_status == "ASSIGNED" and task.assigned_at is None:
        task.assigned_at = now
    elif new_status == "ACCEPTED" and task.accepted_at is None:
        task.accepted_at = now
    elif new_status == "ON_SCENE" and task.arrived_at is None:
        task.arrived_at = now
    elif new_status == "COMPLETED" and task.completed_at is None:
        task.completed_at = now

    # Record status change event
    payload = {}
    if notes:
        payload["notes"] = notes

    await record_status_change(
        db=db,
        entity_type="TASK",
        entity_id=task.id,
        previous_status=previous_status,
        new_status=new_status,
        triggered_by_user_id=triggered_by_user_id,
        payload=payload
    )

    # Publish to Redis (non-blocking)
    try:
        from backend.app.services.pubsub_service import publish_task_update
        await publish_task_update(
            str(task.id),
            {
                "event": "STATUS_CHANGED",
                "entity_type": "TASK",
                "entity_id": str(task.id),
                "new_status": new_status,
                "timestamp": now.isoformat()
            }
        )
    except Exception as e:
        print(f"⚠ Failed to publish task update: {e}")
