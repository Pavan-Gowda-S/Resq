"""
Hospital Routing Agent - Auto-selects nearest hospital with available ICU bed
for HOSPITAL_ADMISSION tasks and atomically holds the bed.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.response_task import ResponseTask
from backend.app.services.resource_service import search_hospitals_by_location
from backend.app.services.reservation_service import create_reservation
from backend.app.services.agent_event_service import log_agent_event
from backend.app.services.pubsub_service import publish_task_update
from shared.constants import TaskStatus
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
    try:
        # Search for hospitals with available ICU beds
        # Returns HospitalSearchResult objects with .organization_id and .hospital_name
        hospitals = await search_hospitals_by_location(
            db=db,
            latitude=lat,
            longitude=lng,
            radius_km=100,
            min_icu_available=1
        )

        if not hospitals:
            logger.warning(f"No hospitals with available ICU beds found near {lat},{lng}")
            return False

        # Pick nearest hospital (already sorted by distance)
        selected = hospitals[0]

        # HospitalSearchResult uses .organization_id and .hospital_name (not .id / .name)
        hosp_id = getattr(selected, "organization_id", None)
        hosp_name = getattr(selected, "hospital_name", "Unknown Hospital")

        if hosp_id is None:
            # Fallback for dict-style result
            hosp_id = selected.get("id") or selected.get("organization_id")
            hosp_name = selected.get("name") or selected.get("hospital_name", "Unknown Hospital")

        if hosp_id is None:
            logger.error(f"Could not extract hospital ID from result: {selected}")
            return False

        # Create atomic reservation
        try:
            reservation = await create_reservation(
                db=db,
                task_id=task.id,
                organization_id=hosp_id,
                resource_type="HOSPITAL_ICU_BED",
                quantity=1,
            )
        except Exception as e:
            logger.error(f"Failed to create reservation for task {task.id}: {e}")
            return False

        # Update task status
        task.assigned_organization_id = hosp_id
        task.status = TaskStatus.ASSIGNED.value
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
                "hospital_id": str(hosp_id),
                "hospital_name": hosp_name,
                "reservation_id": str(reservation.id),
                "candidates_found": len(hospitals),
            },
            confidence_score=0.95,
            incident_id=task.incident_id,
        )

        # Publish Redis update
        try:
            await publish_task_update(task.id, {"status": "ASSIGNED", "hospital": hosp_name})
        except Exception:
            pass

        logger.info(f"Task {task.id} routed to hospital {hosp_name} with reservation {reservation.id}")
        return True

    except Exception as exc:
        logger.error(f"Error in route_to_hospital for task {getattr(task, 'id', None)}: {exc}", exc_info=True)
        return False
