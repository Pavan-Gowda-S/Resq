"""
Offline sync service for processing batched events.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement

from backend.app.models import ResponseTask, Incident, User, AuditLog
from backend.app.schemas.sync import SyncRequest, SyncResponse, SyncConflict, SyncEvent
from backend.app.services.status_service import update_task_status, update_incident_status, record_status_change


async def is_event_already_processed(db: AsyncSession, event_id: UUID) -> bool:
    """
    Check if event_id has already been processed (idempotency check).
    Uses audit_logs table to track processed sync events.
    """
    result = await db.execute(
        select(AuditLog).where(
            AuditLog.action == "SYNC_EVENT"
        ).where(
            AuditLog.details["event_id"].astext == str(event_id)
        )
    )
    return result.scalar_one_or_none() is not None


async def mark_event_processed(
    db: AsyncSession,
    event: SyncEvent,
    device_id: str,
    user_id: UUID
) -> None:
    """Mark event as processed in audit log."""
    audit_log = AuditLog(
        user_id=user_id,
        action="SYNC_EVENT",
        ip_address=None,
        request_route="/api/v1/sync/events",
        details={
            "event_id": str(event.event_id),
            "device_id": device_id,
            "entity_type": event.entity_type,
            "entity_id": str(event.entity_id),
            "action": event.action,
            "client_timestamp": event.client_timestamp.isoformat()
        }
    )
    db.add(audit_log)
    await db.flush()


async def process_task_status_update(
    db: AsyncSession,
    event: SyncEvent,
    user_id: UUID
) -> Optional[SyncConflict]:
    """
    Process UPDATE_STATUS action on TASK entity.
    Returns conflict if any, None on success.
    """
    # Get task
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == event.entity_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"TASK {event.entity_id} not found"
        )

    # Get requested status
    new_status = event.payload.get("status")
    if not new_status:
        return SyncConflict(
            event_id=event.event_id,
            reason="Missing 'status' in payload"
        )

    # Validate status value
    valid_statuses = {
        "PENDING_ASSIGNMENT", "ASSIGNED", "ACCEPTED", "REJECTED",
        "EN_ROUTE", "ON_SCENE", "COMPLETED", "CANCELLED"
    }
    if new_status not in valid_statuses:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"Invalid status: {new_status}",
            current_status=task.status
        )

    # Check for invalid transitions (basic validation)
    # Allow most transitions for offline sync (field responders may skip states)
    # Only block obviously invalid ones
    if task.status == "COMPLETED" and new_status not in ["COMPLETED", "CANCELLED"]:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"Invalid transition: {task.status} → {new_status}",
            current_status=task.status
        )

    # Update task status
    notes = event.payload.get("notes")
    payload = {
        "client_timestamp": event.client_timestamp.isoformat(),
        "synced_from_offline": True
    }
    if notes:
        payload["notes"] = notes

    await update_task_status(
        db=db,
        task=task,
        new_status=new_status,
        triggered_by_user_id=user_id,
        notes=notes
    )

    return None  # Success


async def process_incident_status_update(
    db: AsyncSession,
    event: SyncEvent,
    user_id: UUID
) -> Optional[SyncConflict]:
    """
    Process UPDATE_STATUS action on INCIDENT entity.
    Returns conflict if any, None on success.
    """
    # Get incident
    result = await db.execute(
        select(Incident).where(Incident.id == event.entity_id)
    )
    incident = result.scalar_one_or_none()

    if not incident:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"INCIDENT {event.entity_id} not found"
        )

    # Get requested status
    new_status = event.payload.get("status")
    if not new_status:
        return SyncConflict(
            event_id=event.event_id,
            reason="Missing 'status' in payload"
        )

    # Update incident status
    notes = event.payload.get("notes")
    await update_incident_status(
        db=db,
        incident=incident,
        new_status=new_status,
        triggered_by_user_id=user_id,
        notes=notes
    )

    return None  # Success


async def process_task_location_update(
    db: AsyncSession,
    event: SyncEvent,
    user_id: UUID
) -> Optional[SyncConflict]:
    """
    Process UPDATE_LOCATION action on TASK entity.
    Returns conflict if any, None on success.
    """
    # Get task
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == event.entity_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"TASK {event.entity_id} not found"
        )

    # Get location from payload
    location = event.payload.get("location")
    if not location:
        return SyncConflict(
            event_id=event.event_id,
            reason="Missing 'location' in payload"
        )

    # Validate GeoJSON Point format
    if not isinstance(location, dict) or location.get("type") != "Point":
        return SyncConflict(
            event_id=event.event_id,
            reason="Invalid location format (expected GeoJSON Point)"
        )

    coordinates = location.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) != 2:
        return SyncConflict(
            event_id=event.event_id,
            reason="Invalid coordinates format"
        )

    lon, lat = coordinates

    # Update task location (note: task model doesn't have current_location by default)
    # If current_location field exists, update it; otherwise log to status_event
    try:
        # Record as status event for audit
        await record_status_change(
            db=db,
            entity_type="TASK",
            entity_id=task.id,
            previous_status=task.status,
            new_status=task.status,  # Status unchanged
            triggered_by_user_id=user_id,
            payload={
                "action": "UPDATE_LOCATION",
                "location": location,
                "client_timestamp": event.client_timestamp.isoformat()
            }
        )
    except Exception as e:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"Failed to update location: {str(e)}"
        )

    return None  # Success


async def process_confirm_arrival(
    db: AsyncSession,
    event: SyncEvent,
    user_id: UUID
) -> Optional[SyncConflict]:
    """
    Process CONFIRM_ARRIVAL action on TASK entity.
    Returns conflict if any, None on success.
    """
    # Get task
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == event.entity_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return SyncConflict(
            event_id=event.event_id,
            reason=f"TASK {event.entity_id} not found"
        )

    # Update citizen confirmation
    task.citizen_confirmed_arrival = True
    task.citizen_confirmed_at = event.client_timestamp

    # Record status event
    await record_status_change(
        db=db,
        entity_type="TASK",
        entity_id=task.id,
        previous_status=task.status,
        new_status=task.status,  # Status unchanged
        triggered_by_user_id=user_id,
        payload={
            "event_type": "CITIZEN_CONFIRMED_ARRIVAL",
            "confirmed": True,
            "client_timestamp": event.client_timestamp.isoformat(),
            "feedback_comment": event.payload.get("feedback_comment")
        }
    )

    return None  # Success


async def process_sync_events(
    request: SyncRequest,
    current_user: User,
    db: AsyncSession,
) -> SyncResponse:
    """
    Process batch of offline sync events.

    Args:
        request: Sync request with events batch
        current_user: Authenticated user
        db: Database session

    Returns:
        Sync response with counts and conflicts
    """
    synced_count = 0
    rejected_count = 0
    conflicts = []

    for event in request.events:
        try:
            # 1. Idempotency check
            if await is_event_already_processed(db, event.event_id):
                # Already processed - count as synced but don't reprocess
                synced_count += 1
                continue

            # 2. Process based on action
            conflict = None

            if event.action == "UPDATE_STATUS":
                if event.entity_type == "TASK":
                    conflict = await process_task_status_update(db, event, current_user.id)
                elif event.entity_type == "INCIDENT":
                    conflict = await process_incident_status_update(db, event, current_user.id)
                else:
                    conflict = SyncConflict(
                        event_id=event.event_id,
                        reason=f"Unknown entity_type: {event.entity_type}"
                    )

            elif event.action == "UPDATE_LOCATION":
                if event.entity_type == "TASK":
                    conflict = await process_task_location_update(db, event, current_user.id)
                else:
                    conflict = SyncConflict(
                        event_id=event.event_id,
                        reason=f"UPDATE_LOCATION only supported for TASK entity"
                    )

            elif event.action == "CONFIRM_ARRIVAL":
                if event.entity_type == "TASK":
                    conflict = await process_confirm_arrival(db, event, current_user.id)
                else:
                    conflict = SyncConflict(
                        event_id=event.event_id,
                        reason=f"CONFIRM_ARRIVAL only supported for TASK entity"
                    )

            else:
                conflict = SyncConflict(
                    event_id=event.event_id,
                    reason=f"Unknown action: {event.action}"
                )

            # 3. Update counts and conflicts
            if conflict:
                rejected_count += 1
                conflicts.append(conflict)
            else:
                synced_count += 1
                # Mark as processed
                await mark_event_processed(db, event, request.device_id, current_user.id)

        except Exception as e:
            # Catch-all for unexpected errors
            rejected_count += 1
            conflicts.append(SyncConflict(
                event_id=event.event_id,
                reason=f"Processing error: {str(e)}"
            ))

    # Commit all changes
    await db.commit()

    return SyncResponse(
        synced_count=synced_count,
        rejected_count=rejected_count,
        conflicts=conflicts
    )
