"""
Organizations API router.
Handles organization CRUD operations with PostGIS location support.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from shapely.geometry import Point

from backend.app.database import get_db
from backend.app.models import Organization, User
from backend.app.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListItem,
    GeoJSONPoint,
)
from backend.app.auth import get_current_user

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def geojson_point_to_wkt(geojson: GeoJSONPoint) -> str:
    """Convert GeoJSON Point to WKT format for PostGIS."""
    lon, lat = geojson.coordinates
    return f"POINT({lon} {lat})"


def wkb_to_geojson(wkb_element) -> GeoJSONPoint:
    """Convert PostGIS WKB to GeoJSON Point."""
    shape = to_shape(wkb_element)
    return GeoJSONPoint(
        type="Point",
        coordinates=[shape.x, shape.y]
    )


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new organization.

    **Authorization:** SUPERADMIN only

    **Location Format:** GeoJSON Point with [longitude, latitude]
    """
    # Only SUPERADMIN can create organizations
    if current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPERADMIN can create organizations"
        )

    # Check if registration number already exists (if provided)
    if org_data.registration_number:
        result = await db.execute(
            select(Organization).where(Organization.registration_number == org_data.registration_number)
        )
        existing_org = result.scalar_one_or_none()
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration number already exists"
            )

    # Convert GeoJSON Point to PostGIS format
    location_wkt = geojson_point_to_wkt(org_data.location)

    # Create new organization
    new_org = Organization(
        name=org_data.name,
        type=org_data.type,
        registration_number=org_data.registration_number,
        verification_status=org_data.verification_status,
        contact_email=org_data.contact_email,
        contact_phone=org_data.contact_phone,
        location=WKTElement(location_wkt, srid=4326),
        address=org_data.address,
        district=org_data.district,
    )

    db.add(new_org)
    await db.commit()
    await db.refresh(new_org)

    # Convert response with GeoJSON location
    return OrganizationResponse(
        id=new_org.id,
        name=new_org.name,
        type=new_org.type,
        registration_number=new_org.registration_number,
        verification_status=new_org.verification_status,
        contact_email=new_org.contact_email,
        contact_phone=new_org.contact_phone,
        location=wkb_to_geojson(new_org.location),
        address=new_org.address,
        district=new_org.district,
        created_at=new_org.created_at,
        updated_at=new_org.updated_at,
    )


@router.get("", response_model=List[OrganizationListItem], status_code=status.HTTP_200_OK)
async def list_organizations(
    type: Optional[str] = Query(None, description="Filter by organization type"),
    district: Optional[str] = Query(None, description="Filter by district"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List organizations with optional filtering.

    **Authorization:** Any authenticated user

    **Filters:**
    - type: Organization type (RESCUE, HOSPITAL, AMBULANCE_PROVIDER, etc.)
    - district: District name (e.g., Ernakulam, Wayanad)
    - verification_status: PENDING, VERIFIED, SUSPENDED
    """
    # Build query with filters
    query = select(Organization)

    if type:
        query = query.where(Organization.type == type)
    if district:
        query = query.where(Organization.district == district)
    if verification_status:
        query = query.where(Organization.verification_status == verification_status)

    query = query.offset(skip).limit(limit).order_by(Organization.name)

    result = await db.execute(query)
    organizations = result.scalars().all()

    # Convert to response format with GeoJSON
    return [
        OrganizationListItem(
            id=org.id,
            name=org.name,
            type=org.type,
            verification_status=org.verification_status,
            district=org.district,
            location=wkb_to_geojson(org.location),
        )
        for org in organizations
    ]


@router.get("/{organization_id}", response_model=OrganizationResponse, status_code=status.HTTP_200_OK)
async def get_organization(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get organization details by ID.

    **Authorization:** Any authenticated user
    """
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return OrganizationResponse(
        id=org.id,
        name=org.name,
        type=org.type,
        registration_number=org.registration_number,
        verification_status=org.verification_status,
        contact_email=org.contact_email,
        contact_phone=org.contact_phone,
        location=wkb_to_geojson(org.location),
        address=org.address,
        district=org.district,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )
