"""
Pydantic schemas for incidents, incident reports, and citizen tracking.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from backend.app.schemas.organization import GeoJSONPoint


class IncidentReportCreate(BaseModel):
    """Public citizen SOS report submission schema."""
    reporter_name: Optional[str] = Field(None, max_length=255, description="Reporter name (anonymous allowed)")
    reporter_phone: Optional[str] = Field(None, max_length=50, description="Reporter phone")
    description: str = Field(..., min_length=10, description="Incident description")
    location: GeoJSONPoint = Field(..., description="Incident location (GeoJSON Point)")
    district: str = Field(..., max_length=100, description="District")
    landmark: Optional[str] = Field(None, description="Nearby landmark")
    people_affected: int = Field(1, ge=0, description="Number of people affected")
    source: str = Field("WEB_ANONYMOUS", description="Report source")


class IncidentReportResponse(BaseModel):
    """Incident report response schema."""
    id: UUID
    incident_id: Optional[UUID]
    reporter_name: Optional[str]
    reporter_phone: Optional[str]
    raw_text: str
    reported_location: Optional[GeoJSONPoint]
    reported_landmark: Optional[str]
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentCreate(BaseModel):
    """Internal incident creation schema (for admins/dispatchers)."""
    hazard_type: str = Field(..., description="FLOOD, LANDSLIDE, MEDICAL_EMERGENCY, COLLAPSED_STRUCTURE, FIRE, OTHER")
    description: str = Field(..., min_length=10)
    location: GeoJSONPoint
    district: str = Field(..., max_length=100)
    landmark: Optional[str] = None
    people_affected: int = Field(1, ge=0)
    trapped_count: int = Field(0, ge=0)
    injured_count: int = Field(0, ge=0)
    priority: str = Field("MEDIUM", description="CRITICAL, HIGH, MEDIUM, LOW")


class IncidentResponse(BaseModel):
    """Incident response schema."""
    id: UUID
    incident_number: str
    status: str
    priority: str
    hazard_type: str
    description: str
    location: GeoJSONPoint
    district: str
    landmark: Optional[str]
    people_affected: int
    trapped_count: int
    injured_count: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    """Incident detail with linked tasks and reports."""
    tasks: List["ResponseTaskResponse"] = []
    reports: List[IncidentReportResponse] = []


class IncidentStatusUpdate(BaseModel):
    """Incident status update schema."""
    status: str = Field(..., description="New status: REPORTED, ANALYZING, TRIAGED, DISPATCHING, ACTIVE_RESPONSE, RESOLVED, CLOSED, FALSE_ALARM")
    notes: Optional[str] = Field(None, description="Status change notes")


class TrackingTokenResponse(BaseModel):
    """Tracking token issuance response."""
    incident_id: UUID
    incident_number: str
    status: str
    tracking_token: str
    tracking_url: str
    message: str


class CitizenTaskSummary(BaseModel):
    """Public task summary for citizen tracking (no sensitive data)."""
    task_id: UUID
    task_type: str
    status: str
    responder_type: Optional[str] = Field(None, description="Generic responder type, not personal info")
    eta_minutes: Optional[int] = None


class CitizenTrackResponse(BaseModel):
    """Public incident tracking response for citizens."""
    incident_number: str
    status: str
    reported_at: datetime
    tasks: List[CitizenTaskSummary] = []


# Import for forward reference resolution
from backend.app.schemas.task import ResponseTaskResponse
IncidentDetailResponse.model_rebuild()
