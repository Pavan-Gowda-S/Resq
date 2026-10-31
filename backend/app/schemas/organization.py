"""
Pydantic schemas for organizations.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class GeoJSONPoint(BaseModel):
    """GeoJSON Point schema for location coordinates."""
    type: str = Field("Point", description="GeoJSON type")
    coordinates: list[float] = Field(..., description="[longitude, latitude] array")

    model_config = {"json_schema_extra": {
        "example": {
            "type": "Point",
            "coordinates": [76.2711, 10.8505]
        }
    }}


class OrganizationCreate(BaseModel):
    """Organization creation schema."""
    name: str = Field(..., min_length=2, max_length=255, description="Organization name")
    type: str = Field(..., description="Organization type: RESCUE, HOSPITAL, AMBULANCE_PROVIDER, PHARMACY, BLOOD_BANK, SUPPLIER, CONTROL_ROOM, ADMIN")
    registration_number: Optional[str] = Field(None, max_length=100, description="Official registration number")
    verification_status: str = Field("PENDING", description="Verification status: PENDING, VERIFIED, SUSPENDED")
    contact_email: EmailStr = Field(..., description="Primary contact email")
    contact_phone: str = Field(..., min_length=10, max_length=50, description="Primary contact phone")
    location: GeoJSONPoint = Field(..., description="Geographic location (GeoJSON Point)")
    address: str = Field(..., min_length=5, description="Full address")
    district: str = Field(..., max_length=100, description="District (e.g., Ernakulam, Wayanad)")


class OrganizationUpdate(BaseModel):
    """Organization update schema (partial updates allowed)."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    verification_status: Optional[str] = Field(None, description="PENDING, VERIFIED, SUSPENDED")
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, min_length=10, max_length=50)
    location: Optional[GeoJSONPoint] = None
    address: Optional[str] = Field(None, min_length=5)
    district: Optional[str] = Field(None, max_length=100)


class OrganizationResponse(BaseModel):
    """Organization response schema."""
    id: UUID
    name: str
    type: str
    registration_number: Optional[str]
    verification_status: str
    contact_email: str
    contact_phone: str
    location: GeoJSONPoint
    address: str
    district: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationListItem(BaseModel):
    """Organization list item (summary view)."""
    id: UUID
    name: str
    type: str
    verification_status: str
    district: str
    location: GeoJSONPoint

    model_config = {"from_attributes": True}
