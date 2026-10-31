"""
Resource and capacity management API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import (
    HospitalCapacity,
    AmbulanceStatus,
    ResourceInventory,
    ResourceReservation,
    User,
    Organization
)
from backend.app.schemas.resource import (
    HospitalCapacityUpdate,
    HospitalCapacityResponse,
    HospitalSearchResult,
    AmbulanceStatusResponse,
    AmbulanceLocationUpdate,
    AmbulanceSearchResult,
    ResourceInventoryCreate,
    ResourceInventoryUpdate,
    ResourceInventoryResponse,
    ReservationCreate,
    ReservationResponse,
    ReservationFulfill,
    ReservationRelease,
)
from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.services.resource_service import (
    search_hospitals_by_location,
    search_ambulances_by_location,
    search_inventory,
)
from backend.app.services.reservation_service import (
    create_reservation,
    fulfill_reservation,
    release_reservation,
)
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])


def wkb_to_geojson(wkb_element):
    """Convert PostGIS WKB to GeoJSON Point."""
    if wkb_element is None:
        return None
    shape = to_shape(wkb_element)
    geojson = mapping(shape)
    from backend.app.schemas.organization import GeoJSONPoint
    return GeoJSONPoint(type="Point", coordinates=geojson["coordinates"])


@router.get("/hospitals/search", response_model=dict)
async def search_hospitals(
    lat: float = Query(..., description="Search center latitude"),
    lng: float = Query(..., description="Search center longitude"),
    radius_km: float = Query(50.0, ge=1, le=200, description="Search radius in km"),
    min_icu_available: Optional[int] = Query(None, ge=0),
    min_emergency_available: Optional[int] = Query(None, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search hospitals within radius with availability filtering.
    """
    results = await search_hospitals_by_location(
        db=db,
        latitude=lat,
        longitude=lng,
        radius_km=radius_km,
        min_emergency_available=min_emergency_available,
        min_icu_available=min_icu_available
    )

    return {
        "count": len(results),
        "results": [result.model_dump() for result in results]
    }


@router.get("/hospitals/{organization_id}/capacity", response_model=HospitalCapacityResponse)
async def get_hospital_capacity(
    organization_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get hospital capacity details.
    """
    result = await db.execute(
        select(HospitalCapacity).where(HospitalCapacity.organization_id == organization_id)
    )
    capacity = result.scalar_one_or_none()

    if not capacity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital capacity record not found"
        )

    # Calculate available beds
    available_emergency = (
        capacity.total_emergency_beds -
        capacity.occupied_emergency_beds -
        capacity.reserved_emergency_beds -
        capacity.out_of_service_emergency_beds
    )
    available_icu = (
        capacity.total_icu_beds -
        capacity.occupied_icu_beds -
        capacity.reserved_icu_beds -
        capacity.out_of_service_icu_beds
    )

    return HospitalCapacityResponse(
        id=capacity.id,
        organization_id=capacity.organization_id,
        total_emergency_beds=capacity.total_emergency_beds,
        occupied_emergency_beds=capacity.occupied_emergency_beds,
        reserved_emergency_beds=capacity.reserved_emergency_beds,
        out_of_service_emergency_beds=capacity.out_of_service_emergency_beds,
        available_emergency_beds=available_emergency,
        total_icu_beds=capacity.total_icu_beds,
        occupied_icu_beds=capacity.occupied_icu_beds,
        reserved_icu_beds=capacity.reserved_icu_beds,
        out_of_service_icu_beds=capacity.out_of_service_icu_beds,
        available_icu_beds=available_icu,
        has_oxygen_facility=capacity.has_oxygen_facility,
        has_trauma_center=capacity.has_trauma_center,
        updated_at=capacity.updated_at
    )


@router.put("/hospitals/{organization_id}/capacity", response_model=HospitalCapacityResponse)
async def update_hospital_capacity(
    organization_id: UUID,
    capacity_update: HospitalCapacityUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update hospital capacity (ORG_ADMIN of that hospital or SUPERADMIN).
    """
    # Authorization check
    if current_user.role != "SUPERADMIN":
        if current_user.role != "ORG_ADMIN" or current_user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this hospital's capacity"
            )

    # Get capacity record
    result = await db.execute(
        select(HospitalCapacity).where(HospitalCapacity.organization_id == organization_id)
    )
    capacity = result.scalar_one_or_none()

    if not capacity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hospital capacity record not found"
        )

    # Update fields
    update_data = capacity_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(capacity, field, value)

    await db.commit()
    await db.refresh(capacity)

    # Calculate available beds
    available_emergency = (
        capacity.total_emergency_beds -
        capacity.occupied_emergency_beds -
        capacity.reserved_emergency_beds -
        capacity.out_of_service_emergency_beds
    )
    available_icu = (
        capacity.total_icu_beds -
        capacity.occupied_icu_beds -
        capacity.reserved_icu_beds -
        capacity.out_of_service_icu_beds
    )

    return HospitalCapacityResponse(
        id=capacity.id,
        organization_id=capacity.organization_id,
        total_emergency_beds=capacity.total_emergency_beds,
        occupied_emergency_beds=capacity.occupied_emergency_beds,
        reserved_emergency_beds=capacity.reserved_emergency_beds,
        out_of_service_emergency_beds=capacity.out_of_service_emergency_beds,
        available_emergency_beds=available_emergency,
        total_icu_beds=capacity.total_icu_beds,
        occupied_icu_beds=capacity.occupied_icu_beds,
        reserved_icu_beds=capacity.reserved_icu_beds,
        out_of_service_icu_beds=capacity.out_of_service_icu_beds,
        available_icu_beds=available_icu,
        has_oxygen_facility=capacity.has_oxygen_facility,
        has_trauma_center=capacity.has_trauma_center,
        updated_at=capacity.updated_at
    )


@router.get("/ambulances/search", response_model=dict)
async def search_ambulances(
    lat: float = Query(..., description="Search center latitude"),
    lng: float = Query(..., description="Search center longitude"),
    radius_km: float = Query(50.0, ge=1, le=200, description="Search radius in km"),
    ambulance_type: Optional[str] = Query(None, description="BLS, ALS, NEONATAL, PATIENT_TRANSPORT"),
    only_available: bool = Query(True, description="Only return available ambulances"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search ambulances within radius.
    """
    results = await search_ambulances_by_location(
        db=db,
        latitude=lat,
        longitude=lng,
        radius_km=radius_km,
        ambulance_type=ambulance_type,
        only_available=only_available
    )

    return {
        "count": len(results),
        "results": [result.model_dump() for result in results]
    }


@router.patch("/ambulances/{ambulance_id}/status", response_model=AmbulanceStatusResponse)
async def update_ambulance_status(
    ambulance_id: UUID,
    status_update: AmbulanceLocationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update ambulance status and location.
    """
    result = await db.execute(
        select(AmbulanceStatus).where(AmbulanceStatus.id == ambulance_id)
    )
    ambulance = result.scalar_one_or_none()

    if not ambulance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ambulance not found"
        )

    # Authorization check
    if current_user.role not in ["SUPERADMIN", "CONTROL_ROOM_DISPATCHER"]:
        if current_user.organization_id != ambulance.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this ambulance"
            )

    # Update fields
    if status_update.status:
        ambulance.status = status_update.status

    if status_update.current_location:
        from backend.app.api.v1.incidents import geojson_point_to_wkt
        location_wkt = geojson_point_to_wkt(status_update.current_location)
        ambulance.current_location = WKTElement(location_wkt, srid=4326)

    if status_update.current_task_id is not None:
        ambulance.current_task_id = status_update.current_task_id

    await db.commit()
    await db.refresh(ambulance)

    return AmbulanceStatusResponse(
        id=ambulance.id,
        organization_id=ambulance.organization_id,
        vehicle_number=ambulance.vehicle_number,
        ambulance_type=ambulance.ambulance_type,
        status=ambulance.status,
        current_location=wkb_to_geojson(ambulance.current_location),
        current_task_id=ambulance.current_task_id,
        crew_size=ambulance.crew_size,
        created_at=ambulance.created_at,
        updated_at=ambulance.updated_at
    )


@router.get("/inventory/search", response_model=List[ResourceInventoryResponse])
async def search_resource_inventory(
    category: Optional[str] = Query(None, description="MEDICAL_SUPPLY, RELIEF_MATERIAL, EQUIPMENT, FOOD_WATER"),
    item_code: Optional[str] = Query(None),
    min_available: Optional[int] = Query(None, ge=0),
    organization_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Search resource inventory with filters.
    """
    items = await search_inventory(
        db=db,
        category=category,
        item_code=item_code,
        min_available=min_available,
        organization_id=organization_id
    )

    # Convert to response models
    return [
        ResourceInventoryResponse(
            id=item.id,
            organization_id=item.organization_id,
            category=item.category,
            item_code=item.item_code,
            item_name=item.item_name,
            unit=item.unit,
            total_quantity=item.total_quantity,
            reserved_quantity=item.reserved_quantity,
            available_quantity=item.total_quantity - item.reserved_quantity,
            updated_at=item.updated_at
        )
        for item in items
    ]


@router.post("/inventory", response_model=ResourceInventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_inventory(
    inventory_data: ResourceInventoryCreate,
    current_user: User = Depends(require_role("SUPERADMIN", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create resource inventory item.
    """
    # Authorization check for ORG_ADMIN
    if current_user.role == "ORG_ADMIN":
        if current_user.organization_id != inventory_data.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create inventory for this organization"
            )

    inventory = ResourceInventory(
        organization_id=inventory_data.organization_id,
        category=inventory_data.category,
        item_code=inventory_data.item_code,
        item_name=inventory_data.item_name,
        unit=inventory_data.unit,
        total_quantity=inventory_data.total_quantity,
        reserved_quantity=inventory_data.reserved_quantity
    )

    db.add(inventory)
    await db.commit()
    await db.refresh(inventory)

    return ResourceInventoryResponse(
        id=inventory.id,
        organization_id=inventory.organization_id,
        category=inventory.category,
        item_code=inventory.item_code,
        item_name=inventory.item_name,
        unit=inventory.unit,
        total_quantity=inventory.total_quantity,
        reserved_quantity=inventory.reserved_quantity,
        available_quantity=inventory.total_quantity - inventory.reserved_quantity,
        updated_at=inventory.updated_at
    )


@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_reservation(
    reservation_data: ReservationCreate,
    current_user: User = Depends(require_role("SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "TRIAGE_DOCTOR")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create atomic resource reservation (locks capacity).
    """
    reservation = await create_reservation(
        db=db,
        task_id=reservation_data.task_id,
        organization_id=reservation_data.organization_id,
        resource_type=reservation_data.resource_type,
        quantity=reservation_data.quantity,
        lock_duration_minutes=reservation_data.lock_duration_minutes,
        item_code=reservation_data.item_code
    )

    await db.commit()
    await db.refresh(reservation)

    return ReservationResponse(
        id=reservation.id,
        task_id=reservation.task_id,
        organization_id=reservation.organization_id,
        resource_type=reservation.resource_type,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at
    )


@router.post("/reservations/{reservation_id}/fulfill", response_model=ReservationResponse)
async def fulfill_resource_reservation(
    reservation_id: UUID,
    fulfill_data: ReservationFulfill,
    current_user: User = Depends(require_role("SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    """
    Fulfill reservation (moves bed count from reserved to occupied).
    """
    reservation = await fulfill_reservation(
        db=db,
        reservation_id=reservation_id,
        notes=fulfill_data.notes
    )

    await db.commit()
    await db.refresh(reservation)

    return ReservationResponse(
        id=reservation.id,
        task_id=reservation.task_id,
        organization_id=reservation.organization_id,
        resource_type=reservation.resource_type,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at
    )


@router.post("/reservations/{reservation_id}/release", response_model=ReservationResponse)
async def release_resource_reservation(
    reservation_id: UUID,
    release_data: ReservationRelease,
    current_user: User = Depends(require_role("SUPERADMIN", "CONTROL_ROOM_DISPATCHER", "ORG_ADMIN")),
    db: AsyncSession = Depends(get_db)
):
    """
    Release reservation (restores capacity).
    """
    reservation = await release_reservation(
        db=db,
        reservation_id=reservation_id,
        reason=release_data.reason
    )

    await db.commit()
    await db.refresh(reservation)

    return ReservationResponse(
        id=reservation.id,
        task_id=reservation.task_id,
        organization_id=reservation.organization_id,
        resource_type=reservation.resource_type,
        quantity=reservation.quantity,
        status=reservation.status,
        expires_at=reservation.expires_at,
        created_at=reservation.created_at,
        updated_at=reservation.updated_at
    )


@router.get("/reservations/task/{task_id}", response_model=List[ReservationResponse])
async def get_task_reservations(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all reservations for a task.
    """
    result = await db.execute(
        select(ResourceReservation)
        .where(ResourceReservation.task_id == task_id)
        .order_by(ResourceReservation.created_at.desc())
    )
    reservations = result.scalars().all()

    return [
        ReservationResponse(
            id=r.id,
            task_id=r.task_id,
            organization_id=r.organization_id,
            resource_type=r.resource_type,
            quantity=r.quantity,
            status=r.status,
            expires_at=r.expires_at,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in reservations
    ]
