"""
Task Dispatch Agent - Auto-assigns PENDING_ASSIGNMENT rescue/ambulance tasks
to the nearest verified organization using PostGIS distance.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from backend.app.models.response_task import ResponseTask
from backend.app.models.organization import Organization
from backend.app.services.agent_event_service import log_agent_event
from backend.app.services.pubsub_service import publish_task_update
from shared.constants import TaskStatus
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def dispatch_task(task: ResponseTask, db: AsyncSession) -> bool:
    """
    Auto-assign task to nearest verified organization based on task type.

    Args:
        task: ResponseTask to dispatch
        db: Async database session

    Returns:
        True if successfully dispatched, False otherwise
    """
    try:
        # Determine target org type based on task type
        org_type_map = {
            "RESCUE_EXTRACTION": "RESCUE",
            "SEARCH_AND_RESCUE": "RESCUE",
            "AMBULANCE_TRANSPORT": "AMBULANCE_PROVIDER",
            "FIREFIGHTING": "RESCUE",
        }

        target_org_type = org_type_map.get(task.task_type)
        if not target_org_type:
            logger.debug(f"Task type {task.task_type} does not require dispatch")
            return False

        # Fallback for FIREFIGHTING if needed
        fallback_types = [target_org_type]

        # Load incident relationship if not already loaded
        if not task.incident:
            await db.refresh(task, ["incident"])

        if not task.incident or not task.incident.location:
            logger.warning(f"Task {task.id} has no incident location")
            return False

        # Extract coordinates from incident location (PostGIS point)
        try:
            from shapely import wkb as shapely_wkb
            point = shapely_wkb.loads(bytes(task.incident.location.data), hex=False)
            lat, lng = point.y, point.x
        except Exception as e:
            logger.error(f"Failed to parse incident location: {e}")
            return False

        # Try each org type (primary then fallback)
        org_found = None
        dist_m = None

        for o_type in fallback_types:
            # PostGIS nearest-org query
            query = text("""
                SELECT id, name,
                       ST_Distance(location::geography, ST_SetSRID(ST_Point(:lng, :lat), 4326)::geography) as dist_m
                FROM organizations
                WHERE type = :org_type
                  AND verification_status = 'VERIFIED'
                ORDER BY dist_m ASC
                LIMIT 1
            """)

            result = await db.execute(
                query,
                {"lat": lat, "lng": lng, "org_type": o_type}
            )
            row = result.fetchone()

            if row:
                org_found = row
                dist_m = row.dist_m
                break

        if not org_found:
            logger.warning(f"No verified organization found for task {task.id} type {task.task_type}")
            return False

        # Update task
        task.assigned_organization_id = org_found.id
        task.status = TaskStatus.ASSIGNED.value
        task.assigned_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(task)

        # Log to agent_events
        confidence = max(0.0, 1.0 - (dist_m / 100000)) if dist_m else 0.95
        await log_agent_event(
            db=db,
            agent_name="TaskDispatchAgent",
            action_type="TASK_DISPATCHED",
            input_context={
                "task_id": str(task.id),
                "task_type": task.task_type,
                "incident_id": str(task.incident_id),
            },
            output_decision={
                "assigned_org_id": str(org_found.id),
                "assigned_org_name": org_found.name,
                "distance_m": round(dist_m, 1) if dist_m else 0,
            },
            confidence_score=round(confidence, 3),
            incident_id=task.incident_id,
        )

        # Publish Redis update
        try:
            await publish_task_update(task.id, {"status": "ASSIGNED", "assigned_org": org_found.name})
        except Exception:
            pass

        logger.info(f"Task {task.id} dispatched to {org_found.name} ({dist_m:.1f}m away)")
        return True
    except Exception as exc:
        logger.error(f"Error in dispatch_task for task {getattr(task, 'id', None)}: {exc}", exc_info=True)
        return False
