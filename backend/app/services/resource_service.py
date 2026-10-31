"""
Resource service: Spatial search and capacity queries.
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Distance, ST_MakePoint
from geoalchemy2.types import Geography

from backend.app.models import Organization, HospitalCapacity, AmbulanceStatus, ResourceInventory
from backend.app.schemas.resource import HospitalSearchResult, AmbulanceSearchResult


async def search_hospitals_by_location(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_km: float = 50.0,
    min_emergency_available: Optional[int] = None,
    min_icu_available: Optional[int] = None
) -> List[HospitalSearchResult]:
    """
    Search hospitals within radius using PostGIS spatial queries.

    Args:
        db: Database session
        latitude: Search center latitude
        longitude: Search center longitude
        radius_km: Search radius in kilometers
        min_emergency_available: Minimum available emergency beds filter
        min_icu_available: Minimum available ICU beds filter

    Returns:
        List of hospitals with distance and availability
    """
    # Create search point
    search_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326).cast(Geography)

    # Calculate distance in kilometers
    distance_expr = func.ST_Distance(
        Organization.location,
        search_point
    ) / 1000.0  # Convert meters to kilometers

    # Build query
    query = (
        select(
            Organization.id.label("organization_id"),
            Organization.name.label("hospital_name"),
            distance_expr.label("distance_km"),
            HospitalCapacity.has_trauma_center,
            Organization.location,
            # Calculate available beds
            (
                HospitalCapacity.total_emergency_beds -
                HospitalCapacity.occupied_emergency_beds -
                HospitalCapacity.reserved_emergency_beds -
                HospitalCapacity.out_of_service_emergency_beds
            ).label("available_emergency_beds"),
            (
                HospitalCapacity.total_icu_beds -
                HospitalCapacity.occupied_icu_beds -
                HospitalCapacity.reserved_icu_beds -
                HospitalCapacity.out_of_service_icu_beds
            ).label("available_icu_beds"),
        )
        .join(HospitalCapacity, Organization.id == HospitalCapacity.organization_id)
        .where(
            and_(
                Organization.type == "HOSPITAL",
                Organization.verification_status == "VERIFIED",
                distance_expr <= radius_km
            )
        )
    )

    # Apply availability filters
    if min_emergency_available is not None:
        query = query.where(
            (
                HospitalCapacity.total_emergency_beds -
                HospitalCapacity.occupied_emergency_beds -
                HospitalCapacity.reserved_emergency_beds -
                HospitalCapacity.out_of_service_emergency_beds
            ) >= min_emergency_available
        )

    if min_icu_available is not None:
        query = query.where(
            (
                HospitalCapacity.total_icu_beds -
                HospitalCapacity.occupied_icu_beds -
                HospitalCapacity.reserved_icu_beds -
                HospitalCapacity.out_of_service_icu_beds
            ) >= min_icu_available
        )

    # Order by distance
    query = query.order_by(distance_expr.asc())

    result = await db.execute(query)
    rows = result.all()

    # Convert to response models
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping
    from backend.app.schemas.organization import GeoJSONPoint

    hospitals = []
    for row in rows:
        # Convert PostGIS location to GeoJSON
        shape = to_shape(row.location)
        geojson = mapping(shape)

        hospitals.append(HospitalSearchResult(
            organization_id=row.organization_id,
            hospital_name=row.hospital_name,
            distance_km=round(row.distance_km, 2),
            available_emergency_beds=row.available_emergency_beds,
            available_icu_beds=row.available_icu_beds,
            has_trauma_center=row.has_trauma_center,
            location=GeoJSONPoint(type="Point", coordinates=geojson["coordinates"])
        ))

    return hospitals


async def search_ambulances_by_location(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    radius_km: float = 50.0,
    ambulance_type: Optional[str] = None,
    only_available: bool = True
) -> List[AmbulanceSearchResult]:
    """
    Search ambulances within radius using PostGIS spatial queries.

    Args:
        db: Database session
        latitude: Search center latitude
        longitude: Search center longitude
        radius_km: Search radius in kilometers
        ambulance_type: Filter by ambulance type (BLS, ALS, NEONATAL, PATIENT_TRANSPORT)
        only_available: Only return available ambulances

    Returns:
        List of ambulances with distance
    """
    # Create search point
    search_point = func.ST_SetSRID(ST_MakePoint(longitude, latitude), 4326).cast(Geography)

    # Calculate distance in kilometers
    distance_expr = func.ST_Distance(
        AmbulanceStatus.current_location,
        search_point
    ) / 1000.0

    # Build query
    query = (
        select(
            AmbulanceStatus.id,
            AmbulanceStatus.organization_id,
            AmbulanceStatus.vehicle_number,
            AmbulanceStatus.ambulance_type,
            AmbulanceStatus.status,
            AmbulanceStatus.current_location,
            AmbulanceStatus.crew_size,
            distance_expr.label("distance_km"),
        )
        .where(
            and_(
                AmbulanceStatus.current_location.isnot(None),
                distance_expr <= radius_km
            )
        )
    )

    # Apply filters
    if only_available:
        query = query.where(AmbulanceStatus.status == "AVAILABLE")

    if ambulance_type:
        query = query.where(AmbulanceStatus.ambulance_type == ambulance_type)

    # Order by distance
    query = query.order_by(distance_expr.asc())

    result = await db.execute(query)
    rows = result.all()

    # Convert to response models
    from geoalchemy2.shape import to_shape
    from shapely.geometry import mapping
    from backend.app.schemas.organization import GeoJSONPoint

    ambulances = []
    for row in rows:
        # Convert PostGIS location to GeoJSON
        shape = to_shape(row.current_location)
        geojson = mapping(shape)

        ambulances.append(AmbulanceSearchResult(
            id=row.id,
            organization_id=row.organization_id,
            vehicle_number=row.vehicle_number,
            ambulance_type=row.ambulance_type,
            status=row.status,
            distance_km=round(row.distance_km, 2),
            current_location=GeoJSONPoint(type="Point", coordinates=geojson["coordinates"]),
            crew_size=row.crew_size
        ))

    return ambulances


async def search_inventory(
    db: AsyncSession,
    category: Optional[str] = None,
    item_code: Optional[str] = None,
    min_available: Optional[int] = None,
    organization_id: Optional[UUID] = None
) -> List[ResourceInventory]:
    """
    Search resource inventory with filters.

    Args:
        db: Database session
        category: Filter by category
        item_code: Filter by item code
        min_available: Minimum available quantity
        organization_id: Filter by organization

    Returns:
        List of inventory items
    """
    query = select(ResourceInventory)

    filters = []

    if category:
        filters.append(ResourceInventory.category == category)

    if item_code:
        filters.append(ResourceInventory.item_code == item_code)

    if min_available is not None:
        filters.append(
            (ResourceInventory.total_quantity - ResourceInventory.reserved_quantity) >= min_available
        )

    if organization_id:
        filters.append(ResourceInventory.organization_id == organization_id)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(ResourceInventory.item_name.asc())

    result = await db.execute(query)
    return result.scalars().all()
