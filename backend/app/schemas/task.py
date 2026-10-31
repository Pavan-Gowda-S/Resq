"""
Pydantic schemas for response tasks.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

from backend.app.schemas.organization import GeoJSONPoint


class ResponseTaskCreate(BaseModel):
    """Response task creation schema."""
    task_type: str = Field(..., description="RESCUE_EXTRACTION, AMBULANCE_TRANSPORT, HOSPITAL_ADMISSION, SUPPLY_DELIVERY, RELIEF_CAMP_SHELTER")
    priority: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    target_location: GeoJSONPoint = Field(..., description="Target location (GeoJSON Point)")
    instructions: Optional[str] = Field(None, description="Task instructions")
    parent_task_id: Optional[UUID] = Field(None, description="Parent task ID for dependency chains")
    assigned_organization_id: Optional[UUID] = Field(None, description="Pre-assigned organization")
    assigned_user_id: Optional[UUID] = Field(None, description="Pre-assigned user")


class ResponseTaskResponse(BaseModel):
    """Response task response schema."""
    id: UUID
    incident_id: UUID
    parent_task_id: Optional[UUID]
    task_type: str
    status: str
    priority: str
    assigned_organization_id: Optional[UUID]
    assigned_user_id: Optional[UUID]
    target_location: GeoJSONPoint
    instructions: Optional[str]
    assigned_at: Optional[datetime]
    accepted_at: Optional[datetime]
    arrived_at: Optional[datetime]
    completed_at: Optional[datetime]
    citizen_confirmed_arrival: bool
    citizen_confirmed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResponseTaskStatusUpdate(BaseModel):
    """Task status update schema."""
    status: str = Field(..., description="PENDING_ASSIGNMENT, ASSIGNED, ACCEPTED, REJECTED, EN_ROUTE, ON_SCENE, COMPLETED, CANCELLED")
    notes: Optional[str] = Field(None, description="Status change notes")


class TaskProposal(BaseModel):
    """Single task proposal for multi-task creation."""
    task_type: str
    priority: str
    target_location: GeoJSONPoint
    instructions: Optional[str] = None
    parent_task_id: Optional[UUID] = None


class MultiTaskProposal(BaseModel):
    """Multi-task proposal request."""
    proposals: list[TaskProposal] = Field(..., min_length=1, description="List of task proposals")


class MultiTaskResponse(BaseModel):
    """Multi-task creation response."""
    incident_id: UUID
    created_tasks: list[ResponseTaskResponse]


class TaskAcceptResponse(BaseModel):
    """Task acceptance response schema."""
    task_id: UUID
    status: str
    updated_at: datetime


class CitizenArrivalConfirm(BaseModel):
    """Citizen arrival confirmation request schema."""
    task_id: UUID
    confirmed: bool
    feedback_comment: Optional[str] = Field(None, description="Optional citizen feedback")


class CitizenArrivalResponse(BaseModel):
    """Citizen arrival confirmation response schema."""
    task_id: UUID
    confirmed: bool
    confirmed_at: datetime
