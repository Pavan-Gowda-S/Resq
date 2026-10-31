"""
RESQ Real-time and Audit Event Schemas.
Used for Redis Pub/Sub, WebSockets, and asynchronous agent triggers.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class BaseEvent(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0"

class IncidentCreatedEvent(BaseEvent):
    event_type: str = "incident.created"
    incident_id: str
    priority: str
    hazard_type: str
    district: str
    coordinates: list[float]

class TaskDispatchedEvent(BaseEvent):
    event_type: str = "task.dispatched"
    task_id: str
    incident_id: str
    task_type: str
    assigned_org_id: str

class ResourceReservedEvent(BaseEvent):
    event_type: str = "resource.reserved"
    reservation_id: str
    task_id: str
    resource_type: str
    quantity: int
    expires_at: datetime

class ArrivalConfirmedEvent(BaseEvent):
    event_type: str = "arrival.confirmed"
    task_id: str
    confirmed_by: str  # "RESPONDER" or "CITIZEN"
    timestamp: datetime
