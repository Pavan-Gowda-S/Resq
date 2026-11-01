"""
Hospital Routing Agent - Auto-selects nearest hospital with available ICU bed
for HOSPITAL_ADMISSION tasks and atomically holds the bed.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.response_task import ResponseTask, TaskStatus
from app.services.resource_service import search_hospitals_by_location
from app.services.reservation_service import create_reservation
from app.services.agent_event_service import log_agent_event
from app.services.pubsub_service import publish_task_update
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def route_to_hospital(task: ResponseTask, db: AsyncSession, lat: float, lng: float) -> bool:
    """
    Auto-select nearest hospital with available ICU bed and create atomic reservation.

    Args:
        task: ResponseTask requiring hospital admission
        db: Async database session
        lat: Search latitude
        lng: Search longitude

    Returns:
        True if successfully routed, False otherwise
    """
    # Search for hospitals with available ICU beds
    hospitals = await search_hospitals_by_location(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=100,
        min_icu_available=1
    )

    if not hospitals:
        logger.warning(f"No hospitals with available ICU beds found near {lat},{lng}")
        return False

    # Pick nearest hospital (already sorted by distance)
    selected_hospital = hospitals[0]

    # Create atomic reservation
    try:
        reservation = await create_reservation(
            db=db,
            task_id=task.id,
            organization_id=selected_hospital.id,
            resource_type="HOSPITAL_ICU_BED",
            quantity=1,
        )
    except Exception as e:
        logger.error(f"Failed to create reservation for task {task.id}: {e}")
        return False

    # Update task
    task.assigned_organization_id = selected_hospital.id
    task.status = TaskStatus.ASSIGNED
    task.assigned_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(task)

    # Log to agent_events
    await log_agent_event(
        db=db,
        agent_name="HospitalRoutingAgent",
        action_type="HOSPITAL_ASSIGNED",
        input_context={
            "task_id": str(task.id),
            "incident_id": str(task.incident_id),
            "search_lat": lat,
            "search_lng": lng,
        },
        output_decision={
            "hospital_id": str(selected_hospital.id),
            "hospital_name": selected_hospital.name,
            "reservation_id": str(reservation.id),
            "candidates_found": len(hospitals),
        },
        confidence_score=0.95,
        incident_id=task.incident_id,
        task_id=task.id,
    )

    # Publish Redis update
    await publish_task_update(task.id, {"status": "ASSIGNED", "hospital": selected_hospital.name})

    logger.info(f"Task {task.id} routed to hospital {selected_hospital.name} with reservation {reservation.id}")
    return True
