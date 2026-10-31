"""
Pydantic schemas for resource and capacity management.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, computed_field

from backend.app.schemas.organization import GeoJSONPoint


# Hospital Capacity Schemas

class HospitalCapacityUpdate(BaseModel):
    """Hospital capacity update schema."""
    total_emergency_beds: Optional[int] = Field(None, ge=0)
    occupied_emergency_beds: Optional[int] = Field(None, ge=0)
    reserved_emergency_beds: Optional[int] = Field(None, ge=0)
    out_of_service_emergency_beds: Optional[int] = Field(None, ge=0)

    total_icu_beds: Optional[int] = Field(None, ge=0)
    occupied_icu_beds: Optional[int] = Field(None, ge=0)
    reserved_icu_beds: Optional[int] = Field(None, ge=0)
    out_of_service_icu_beds: Optional[int] = Field(None, ge=0)

    has_oxygen_facility: Optional[bool] = None
    has_trauma_center: Optional[bool] = None


class HospitalCapacityResponse(BaseModel):
    """Hospital capacity response schema."""
    id: UUID
    organization_id: UUID
    total_emergency_beds: int
    occupied_emergency_beds: int
    reserved_emergency_beds: int
    out_of_service_emergency_beds: int
    available_emergency_beds: int

    total_icu_beds: int
    occupied_icu_beds: int
    reserved_icu_beds: int
    out_of_service_icu_beds: int
    available_icu_beds: int

    has_oxygen_facility: bool
    has_trauma_center: bool

    updated_at: datetime

    model_config = {"from_attributes": True}


class HospitalSearchResult(BaseModel):
    """Hospital search result with distance and availability."""
    organization_id: UUID
    hospital_name: str
    distance_km: float
    available_emergency_beds: int
    available_icu_beds: int
    has_trauma_center: bool
    location: GeoJSONPoint


# Ambulance Schemas

class AmbulanceStatusResponse(BaseModel):
    """Ambulance status response schema."""
    id: UUID
    organization_id: UUID
    vehicle_number: str
    ambulance_type: str
    status: str
    current_location: Optional[GeoJSONPoint]
    current_task_id: Optional[UUID]
    crew_size: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AmbulanceLocationUpdate(BaseModel):
    """Ambulance location and status update schema."""
    status: Optional[str] = Field(None, description="AVAILABLE, EN_ROUTE, ON_SCENE, TRANSPORTING, AT_HOSPITAL, OUT_OF_SERVICE, MAINTENANCE")
    current_location: Optional[GeoJSONPoint] = None
    current_task_id: Optional[UUID] = None


class AmbulanceSearchResult(BaseModel):
    """Ambulance search result with distance."""
    id: UUID
    organization_id: UUID
    vehicle_number: str
    ambulance_type: str
    status: str
    distance_km: float
    current_location: GeoJSONPoint
    crew_size: int


# Resource Inventory Schemas

class ResourceInventoryCreate(BaseModel):
    """Resource inventory creation schema."""
    organization_id: UUID
    category: str = Field(..., description="MEDICAL_SUPPLY, RELIEF_MATERIAL, EQUIPMENT, FOOD_WATER")
    item_code: str = Field(..., max_length=100)
    item_name: str = Field(..., max_length=255)
    unit: str = Field(..., max_length=50, description="e.g., UNITS, LITERS, KG, PIECES")
    total_quantity: int = Field(..., ge=0)
    reserved_quantity: int = Field(0, ge=0)


class ResourceInventoryUpdate(BaseModel):
    """Resource inventory update schema."""
    total_quantity: Optional[int] = Field(None, ge=0)
    reserved_quantity: Optional[int] = Field(None, ge=0)


class ResourceInventoryResponse(BaseModel):
    """Resource inventory response schema."""
    id: UUID
    organization_id: UUID
    category: str
    item_code: str
    item_name: str
    unit: str
    total_quantity: int
    reserved_quantity: int
    available_quantity: int
    updated_at: datetime

    model_config = {"from_attributes": True}


# Resource Reservation Schemas

class ReservationCreate(BaseModel):
    """Resource reservation creation schema."""
    task_id: UUID
    organization_id: UUID
    resource_type: str = Field(..., description="HOSPITAL_EMERGENCY_BED, HOSPITAL_ICU_BED, AMBULANCE, MEDICAL_SUPPLY, RELIEF_MATERIAL")
    quantity: int = Field(..., ge=1)
    lock_duration_minutes: int = Field(30, ge=1, le=1440, description="Default 30 minutes, max 24 hours")
    item_code: Optional[str] = Field(None, description="Required for inventory items")


class ReservationResponse(BaseModel):
    """Resource reservation response schema."""
    id: UUID
    task_id: UUID
    organization_id: UUID
    resource_type: str
    quantity: int
    status: str
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def reservation_id(self) -> UUID:
        return self.id

    model_config = {"from_attributes": True}


class ReservationFulfill(BaseModel):
    """Reservation fulfillment schema."""
    notes: Optional[str] = Field(None, description="Fulfillment notes")


class ReservationRelease(BaseModel):
    """Reservation release schema."""
    reason: Optional[str] = Field(None, description="Release reason")
