"""
Response task management API endpoints.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import ResponseTask, User
from backend.app.schemas.task import (
    ResponseTaskResponse,
    ResponseTaskStatusUpdate,
    TaskAcceptResponse,
)
from backend.app.schemas.organization import GeoJSONPoint
from backend.app.auth.dependencies import get_current_user
from backend.app.services.status_service import update_task_status, record_status_change
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKTElement
from shapely.geometry import mapping
from datetime import datetime, timezone

router = APIRouter(prefix="/tasks", tags=["tasks"])


def wkb_to_geojson(wkb_element) -> GeoJSONPoint:
    """Convert PostGIS WKB to GeoJSON Point."""
    if wkb_element is None:
        return None
    shape = to_shape(wkb_element)
    geojson = mapping(shape)
    return GeoJSONPoint(type="Point", coordinates=geojson["coordinates"])


@router.get("/{task_id}", response_model=ResponseTaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get task details (authenticated).
    """
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Multi-tenant and role authorization check
    if current_user.role not in ("SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR"):
        is_assigned = (
            task.assigned_user_id == current_user.id or
            (current_user.organization_id is not None and task.assigned_organization_id == current_user.organization_id)
        )
        if not is_assigned:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this task"
            )

    return ResponseTaskResponse(
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


@router.patch("/{task_id}/accept", response_model=TaskAcceptResponse)
async def accept_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Responder accepts assigned task.

    Authorization: assigned user or dispatcher/admin.
    """
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Authorization: user must be assigned to task OR have dispatcher/admin role
    authorized_roles = ["SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR"]
    is_assigned = (
        task.assigned_user_id == current_user.id or
        task.assigned_organization_id == current_user.organization_id
    )
    is_dispatcher = current_user.role in authorized_roles

    if not (is_assigned or is_dispatcher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to accept this task"
        )

    # Verify task is in ASSIGNED status
    if task.status != "ASSIGNED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot accept task with status {task.status}. Task must be in ASSIGNED status."
        )

    # Update task
    previous_status = task.status
    task.status = "ACCEPTED"
    task.accepted_at = datetime.now(timezone.utc)

    # Record status change
    await record_status_change(
        db=db,
        entity_type="TASK",
        entity_id=task.id,
        previous_status=previous_status,
        new_status="ACCEPTED",
        triggered_by_user_id=current_user.id,
        payload={}
    )

    await db.commit()
    await db.refresh(task)

    return TaskAcceptResponse(
        task_id=task.id,
        status=task.status,
        updated_at=task.updated_at
    )


@router.patch("/{task_id}/reject", response_model=TaskAcceptResponse)
async def reject_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Responder rejects assigned task.

    Authorization: assigned user or dispatcher/admin.
    """
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Authorization: user must be assigned to task OR have dispatcher/admin role
    authorized_roles = ["SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR"]
    is_assigned = (
        task.assigned_user_id == current_user.id or
        task.assigned_organization_id == current_user.organization_id
    )
    is_dispatcher = current_user.role in authorized_roles

    if not (is_assigned or is_dispatcher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reject this task"
        )

    # Verify task is in ASSIGNED status
    if task.status != "ASSIGNED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot reject task with status {task.status}. Task must be in ASSIGNED status."
        )

    # Update task
    previous_status = task.status
    task.status = "PENDING_ASSIGNMENT"
    task.accepted_at = None

    # Record status change
    await record_status_change(
        db=db,
        entity_type="TASK",
        entity_id=task.id,
        previous_status=previous_status,
        new_status="PENDING_ASSIGNMENT",
        triggered_by_user_id=current_user.id,
        payload={}
    )

    await db.commit()
    await db.refresh(task)

    return TaskAcceptResponse(
        task_id=task.id,
        status=task.status,
        updated_at=task.updated_at
    )


@router.patch("/{task_id}/status", response_model=ResponseTaskResponse)
async def update_task_status_endpoint(
    task_id: UUID,
    status_update: ResponseTaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update task status (authenticated).

    Field responders can update their own tasks, dispatchers can update any task.
    """
    result = await db.execute(
        select(ResponseTask).where(ResponseTask.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Authorization: user must be assigned to task OR have dispatcher/admin role
    authorized_roles = ["SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR"]
    is_assigned = task.assigned_user_id == current_user.id
    is_dispatcher = current_user.role in authorized_roles

    if not (is_assigned or is_dispatcher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this task"
        )

    # Update status using service
    await update_task_status(
        db=db,
        task=task,
        new_status=status_update.status,
        triggered_by_user_id=current_user.id,
        notes=status_update.notes
    )

    await db.commit()
    await db.refresh(task)

    return ResponseTaskResponse(
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
