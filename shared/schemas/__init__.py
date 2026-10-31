"""
RESQ Shared Pydantic Data Contracts.
Common data transfer models used for cross-tier validation.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from shared.constants import (
    IncidentStatus,
    UrgencyPriority,
    HazardType,
    TaskType,
    TaskStatus,
    OrganizationType
)

class GeoPoint(BaseModel):
    type: str = Field(default="Point", pattern="^Point$")
    coordinates: List[float] = Field(..., description="[longitude, latitude]")

class IncidentReportCreate(BaseModel):
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    description: str = Field(..., min_length=5)
    location: Optional[GeoPoint] = None
    district: str
    landmark: Optional[str] = None
    people_affected: int = Field(default=1, ge=1)
    source: str = "WEB_ANONYMOUS"

class IncidentReportResponse(BaseModel):
    incident_id: str
    incident_number: str
    status: IncidentStatus
    tracking_token: str
    tracking_url: str
    message: str

class ResponseTaskProposal(BaseModel):
    task_type: TaskType
    priority: UrgencyPriority
    target_location: GeoPoint
    instructions: Optional[str] = None
    parent_task_id: Optional[str] = None

class TaskProposalsPayload(BaseModel):
    proposals: List[ResponseTaskProposal]

class TrackingTaskItem(BaseModel):
    task_id: str
    task_type: TaskType
    status: TaskStatus
    responder_type: Optional[str] = None
    eta_minutes: Optional[int] = None

class IncidentTrackingResponse(BaseModel):
    incident_number: str
    status: IncidentStatus
    reported_at: datetime
    tasks: List[TrackingTaskItem] = []

class SyncEventItem(BaseModel):
    event_id: str
    entity_type: str
    entity_id: str
    action: str
    payload: Dict[str, Any]
    client_timestamp: datetime
