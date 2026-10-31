"""
Incident management API endpoints.
"""
import os
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import Incident, IncidentReport, ResponseTask, User
from backend.app.schemas.incident import (
    IncidentReportCreate,
    IncidentResponse,
    IncidentDetailResponse,
    IncidentStatusUpdate,
    TrackingTokenResponse,
    CitizenTrackResponse,
    CitizenTaskSummary,
)
from backend.app.schemas.task import (
    ResponseTaskCreate,
    ResponseTaskResponse,
    MultiTaskProposal,
    MultiTaskResponse,
    CitizenArrivalConfirm,
    CitizenArrivalResponse,
)
from backend.app.schemas.organization import GeoJSONPoint
from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.services.incident_service import (
    generate_unique_incident_number,
    create_tracking_token,
)
from backend.app.services.status_service import (
    record_status_change,
    update_incident_status,
)
from geoalchemy2.elements import WKTElement
from geoalchemy2.types import Geography
from sqlalchemy import func
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

router = APIRouter(prefix="/incidents", tags=["incidents"])

# Conditional rate limiter import
if os.getenv("TESTING") != "1":
    from backend.app.middleware.rate_limiter import limiter
else:
    # Mock limiter for testing
    class MockLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = MockLimiter()


def geojson_point_to_wkt(geojson: GeoJSONPoint) -> str:
    """Convert GeoJSON Point to WKT format."""
    lon, lat = geojson.coordinates
    return f"POINT({lon} {lat})"


def wkb_to_geojson(wkb_element) -> GeoJSONPoint:
    """Convert PostGIS WKB to GeoJSON Point."""
    if wkb_element is None:
        return None
    shape = to_shape(wkb_element)
    geojson = mapping(shape)
    return GeoJSONPoint(type="Point", coordinates=geojson["coordinates"])


@router.post("/report", response_model=TrackingTokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def report_incident(
    request: Request,
    report_data: IncidentReportCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for citizens to report emergencies (unauthenticated).

    Creates both an incident and an incident_report, issues a tracking token.
    """
    # Generate unique incident number
    incident_number = await generate_unique_incident_number(db)

    # Convert GeoJSON to WKT for PostGIS
    location_wkt = geojson_point_to_wkt(report_data.location)

    # Create incident
    incident = Incident(
        incident_number=incident_number,
        status="REPORTED",
        priority="MEDIUM",  # Default priority, will be triaged
        hazard_type="OTHER",  # Will be classified during triage
        description=report_data.description,
        location=WKTElement(location_wkt, srid=4326),
        district=report_data.district,
        landmark=report_data.landmark,
        people_affected=report_data.people_affected,
        trapped_count=0,
        injured_count=0,
    )
    db.add(incident)
    await db.flush()  # Get incident.id

    # Create incident report
    incident_report = IncidentReport(
        incident_id=incident.id,
        reporter_name=report_data.reporter_name,
        reporter_phone=report_data.reporter_phone,
        raw_text=report_data.description,
        reported_location=WKTElement(location_wkt, srid=4326),
        reported_landmark=report_data.landmark,
        source=report_data.source,
    )
    db.add(incident_report)

    # Record initial status
    await record_status_change(
        db=db,
        entity_type="INCIDENT",
        entity_id=incident.id,
        previous_status=None,
        new_status="REPORTED",
        triggered_by_user_id=None,
        payload={"source": report_data.source}
    )

    # Create tracking token
    tracking_token = await create_tracking_token(
        db=db,
        incident_id=incident.id,
        citizen_phone=report_data.reporter_phone,
    )

    await db.commit()
    await db.refresh(incident)

    # Generate tracking URL
    tracking_url = f"/api/v1/incidents/track/{tracking_token.token}"

    return TrackingTokenResponse(
        incident_id=incident.id,
        incident_number=incident.incident_number,
        status=incident.status,
        tracking_token=tracking_token.token,
        tracking_url=tracking_url,
        message="Your emergency report has been received. Use the tracking token to check status."
    )


@router.get("/track/{token}", response_model=CitizenTrackResponse)
async def track_incident(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for citizens to track their incident (unauthenticated).

    Returns incident status and non-sensitive task information.
    """
    # Find tracking token
    from backend.app.models import TrackingToken
    from datetime import datetime, timezone

    result = await db.execute(
        select(TrackingToken).where(TrackingToken.token == token)
    )
    tracking_token = result.scalar_one_or_none()

    if not tracking_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid tracking token"
        )

    # Check expiration
    if tracking_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Tracking token has expired"
        )

    # Get incident with tasks
    result = await db.execute(
        select(Incident)
        .where(Incident.id == tracking_token.incident_id)
        .options(selectinload(Incident.tasks))
    )
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found"
        )

    # Build citizen-safe task summaries (no sensitive data)
    task_summaries = []
    for task in incident.tasks:
        # Map task type to generic responder type
        responder_type_map = {
            "RESCUE_EXTRACTION": "Rescue Team",
            "AMBULANCE_TRANSPORT": "Ambulance",
            "HOSPITAL_ADMISSION": "Hospital",
            "SUPPLY_DELIVERY": "Supply Team",
            "RELIEF_CAMP_SHELTER": "Relief Camp",
        }

        task_summaries.append(CitizenTaskSummary(
            task_id=task.id,
            task_type=task.task_type,
            status=task.status,
            responder_type=responder_type_map.get(task.task_type, "Response Team"),
            eta_minutes=None,  # Could calculate based on task status
        ))

    return CitizenTrackResponse(
        incident_number=incident.incident_number,
        status=incident.status,
        reported_at=incident.created_at,
        tasks=task_summaries,
    )


@router.get("/duplicates", response_model=List[dict])
async def check_incident_duplicates(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_m: int = Query(200, ge=1, le=5000, description="Search radius in meters"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Check for nearby duplicate incidents within radius.
    """
    search_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326).cast(Geography)
    distance_expr = func.ST_Distance(Incident.location, search_point)

    query = (
        select(
            Incident.id,
            Incident.incident_number,
            distance_expr.label("distance_m"),
            Incident.status,
            Incident.created_at
        )
        .where(
            func.ST_DWithin(Incident.location, search_point, radius_m),
            Incident.status.notin_(["RESOLVED", "CLOSED", "FALSE_ALARM"])
        )
        .order_by("distance_m")
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "incident_id": str(row.id),
            "distance_m": float(row.distance_m),
            "incident_number": row.incident_number,
            "status": row.status
        }
        for row in rows
    ]


@router.get("", response_model=List[IncidentResponse])
async def list_incidents(
    status_filter: Optional[str] = Query(None, alias="status"),
    district: Optional[str] = None,
    priority: Optional[str] = None,
    hazard_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List incidents with filtering (authenticated).
    """
    query = select(Incident)

    # Apply filters
    filters = []
    if status_filter:
        filters.append(Incident.status == status_filter)
    if district:
        filters.append(Incident.district == district)
    if priority:
        filters.append(Incident.priority == priority)
    if hazard_type:
        filters.append(Incident.hazard_type == hazard_type)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(Incident.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    incidents = result.scalars().all()

    # Convert to response models with GeoJSON
    response = []
    for incident in incidents:
        incident_dict = {
            "id": incident.id,
            "incident_number": incident.incident_number,
            "status": incident.status,
            "priority": incident.priority,
            "hazard_type": incident.hazard_type,
            "description": incident.description,
            "location": wkb_to_geojson(incident.location),
            "district": incident.district,
            "landmark": incident.landmark,
            "people_affected": incident.people_affected,
            "trapped_count": incident.trapped_count,
            "injured_count": incident.injured_count,
            "created_at": incident.created_at,
            "updated_at": incident.updated_at,
            "closed_at": incident.closed_at,
        }
        response.append(IncidentResponse(**incident_dict))

    return response


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get incident details with linked tasks and reports (authenticated).
    """
    result = await db.execute(
        select(Incident)
        .where(Incident.id == incident_id)
        .options(selectinload(Incident.tasks), selectinload(Incident.reports))
    )
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found"
        )

    # Build response with GeoJSON conversions
    incident_dict = {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "status": incident.status,
        "priority": incident.priority,
        "hazard_type": incident.hazard_type,
        "description": incident.description,
        "location": wkb_to_geojson(incident.location),
        "district": incident.district,
        "landmark": incident.landmark,
        "people_affected": incident.people_affected,
        "trapped_count": incident.trapped_count,
        "injured_count": incident.injured_count,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
        "closed_at": incident.closed_at,
        "tasks": [
            {
                "id": task.id,
                "incident_id": task.incident_id,
                "parent_task_id": task.parent_task_id,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
                "assigned_organization_id": task.assigned_organization_id,
                "assigned_user_id": task.assigned_user_id,
                "target_location": wkb_to_geojson(task.target_location),
                "instructions": task.instructions,
                "assigned_at": task.assigned_at,
                "accepted_at": task.accepted_at,
                "arrived_at": task.arrived_at,
                "completed_at": task.completed_at,
                "citizen_confirmed_arrival": task.citizen_confirmed_arrival,
                "citizen_confirmed_at": task.citizen_confirmed_at,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
            for task in incident.tasks
        ],
        "reports": [
            {
                "id": report.id,
                "incident_id": report.incident_id,
                "reporter_name": report.reporter_name,
                "reporter_phone": report.reporter_phone,
                "raw_text": report.raw_text,
                "reported_location": wkb_to_geojson(report.reported_location),
                "reported_landmark": report.reported_landmark,
                "source": report.source,
                "created_at": report.created_at,
            }
            for report in incident.reports
        ],
    }

    return IncidentDetailResponse(**incident_dict)


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
async def update_incident_status_endpoint(
    incident_id: UUID,
    status_update: IncidentStatusUpdate,
    current_user: User = Depends(require_role("SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR")),
    db: AsyncSession = Depends(get_db)
):
    """
    Update incident status (authenticated, authorized roles only).
    """
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found"
        )

    # Update status using service
    await update_incident_status(
        db=db,
        incident=incident,
        new_status=status_update.status,
        triggered_by_user_id=current_user.id,
        notes=status_update.notes
    )

    await db.commit()
    await db.refresh(incident)

    # Return response with GeoJSON
    incident_dict = {
        "id": incident.id,
        "incident_number": incident.incident_number,
        "status": incident.status,
        "priority": incident.priority,
        "hazard_type": incident.hazard_type,
        "description": incident.description,
        "location": wkb_to_geojson(incident.location),
        "district": incident.district,
        "landmark": incident.landmark,
        "people_affected": incident.people_affected,
        "trapped_count": incident.trapped_count,
        "injured_count": incident.injured_count,
        "created_at": incident.created_at,
        "updated_at": incident.updated_at,
        "closed_at": incident.closed_at,
    }

    return IncidentResponse(**incident_dict)


@router.post("/{incident_id}/tasks", response_model=MultiTaskResponse, status_code=status.HTTP_201_CREATED)
@router.post("/{incident_id}/tasks/propose", response_model=MultiTaskResponse, status_code=status.HTTP_201_CREATED)
async def create_incident_tasks(
    incident_id: UUID,
    task_proposal: MultiTaskProposal,
    current_user: User = Depends(require_role("SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create multiple linked response tasks for an incident (authenticated, authorized roles only).
    """
    # Verify incident exists
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found"
        )

    # Create tasks
    created_tasks = []
    for proposal in task_proposal.proposals:
        location_wkt = geojson_point_to_wkt(proposal.target_location)

        task = ResponseTask(
            incident_id=incident_id,
            parent_task_id=proposal.parent_task_id,
            task_type=proposal.task_type,
            status="PENDING_ASSIGNMENT",
            priority=proposal.priority,
            target_location=WKTElement(location_wkt, srid=4326),
            instructions=proposal.instructions,
            citizen_confirmed_arrival=False,
        )
        db.add(task)
        await db.flush()  # Get task.id

        # Record initial status
        await record_status_change(
            db=db,
            entity_type="TASK",
            entity_id=task.id,
            previous_status=None,
            new_status="PENDING_ASSIGNMENT",
            triggered_by_user_id=current_user.id,
            payload={"task_type": task.task_type}
        )

        created_tasks.append(task)

    await db.commit()

    # Build response
    task_responses = [
        ResponseTaskResponse(
            id=task.id,
            incident_id=task.incident_id,
            parent_task_id=task.parent_task_id,
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            assigned_organization_id=task.assigned_organization_id,
            assigned_user_id=task.assigned_user_id,
            target_location=wkb_to_geojson(task.target_location),
            instructions=task.instructions,
            assigned_at=task.assigned_at,
            accepted_at=task.accepted_at,
            arrived_at=task.arrived_at,
            completed_at=task.completed_at,
            citizen_confirmed_arrival=task.citizen_confirmed_arrival,
            citizen_confirmed_at=task.citizen_confirmed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in created_tasks
    ]

    return MultiTaskResponse(
        incident_id=incident_id,
        created_tasks=task_responses
    )


@router.get("/{incident_id}/tasks", response_model=List[ResponseTaskResponse])
async def list_incident_tasks(
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all tasks for an incident (authenticated).
    """
    # Verify incident exists
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found"
        )

    # Get tasks
    result = await db.execute(
        select(ResponseTask)
        .where(ResponseTask.incident_id == incident_id)
        .order_by(ResponseTask.created_at.asc())
    )
    tasks = result.scalars().all()

    # Build response
    return [
        ResponseTaskResponse(
            id=task.id,
            incident_id=task.incident_id,
            parent_task_id=task.parent_task_id,
            task_type=task.task_type,
            status=task.status,
            priority=task.priority,
            assigned_organization_id=task.assigned_organization_id,
            assigned_user_id=task.assigned_user_id,
            target_location=wkb_to_geojson(task.target_location),
            instructions=task.instructions,
            assigned_at=task.assigned_at,
            accepted_at=task.accepted_at,
            arrived_at=task.arrived_at,
            completed_at=task.completed_at,
            citizen_confirmed_arrival=task.citizen_confirmed_arrival,
            citizen_confirmed_at=task.citizen_confirmed_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )
        for task in tasks
    ]


@router.post("/track/{token}/confirm-arrival", response_model=CitizenArrivalResponse)
@limiter.limit("20/minute")
async def confirm_arrival(
    request: Request,
    token: str,
    confirm_data: CitizenArrivalConfirm,
    db: AsyncSession = Depends(get_db)
):
    """
    Public endpoint for citizens to confirm responder arrival (unauthenticated).

    Uses tracking token for authorization.
    """
    from backend.app.models import TrackingToken
    from datetime import datetime, timezone

    # Find tracking token
    result = await db.execute(
        select(TrackingToken).where(TrackingToken.token == token)
    )
    tracking_token = result.scalar_one_or_none()

    if not tracking_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid tracking token"
        )

    # Check expiration
    if tracking_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking token has expired"
        )

    # Get task
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == confirm_data.task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Verify task belongs to incident associated with tracking token
    if task.incident_id != tracking_token.incident_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Task does not belong to this incident"
        )

    # Update task with citizen confirmation
    task.citizen_confirmed_arrival = confirm_data.confirmed
    task.citizen_confirmed_at = datetime.now(timezone.utc)

    # Record status change event
    await record_status_change(
        db=db,
        entity_type="TASK",
        entity_id=task.id,
        previous_status=task.status,
        new_status=task.status,  # Status doesn't change, just recording the confirmation
        triggered_by_user_id=None,  # Public endpoint
        payload={
            "event_type": "CITIZEN_CONFIRMED_ARRIVAL",
            "confirmed": confirm_data.confirmed,
            "feedback_comment": confirm_data.feedback_comment
        }
    )

    await db.commit()
    await db.refresh(task)

    return CitizenArrivalResponse(
        task_id=task.id,
        confirmed=task.citizen_confirmed_arrival,
        confirmed_at=task.citizen_confirmed_at
    )
