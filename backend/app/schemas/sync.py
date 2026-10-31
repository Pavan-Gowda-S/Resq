"""
Pydantic schemas for offline sync API.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Any, Optional


class SyncEvent(BaseModel):
    """Single sync event from offline queue."""
    event_id: UUID = Field(..., description="UUIDv4 for idempotency")
    entity_type: str = Field(..., description="TASK or INCIDENT")
    entity_id: UUID = Field(..., description="ID of the task or incident")
    action: str = Field(..., description="UPDATE_STATUS, UPDATE_LOCATION, or CONFIRM_ARRIVAL")
    payload: dict[str, Any] = Field(..., description="Action-specific data")
    client_timestamp: datetime = Field(..., description="When event happened on client (offline)")


class SyncRequest(BaseModel):
    """Batch sync request from offline device."""
    device_id: str = Field(..., max_length=100, description="Device identifier")
    events: list[SyncEvent] = Field(..., min_length=1, max_length=50, description="Events to sync")


class SyncConflict(BaseModel):
    """Conflict encountered during sync."""
    event_id: UUID
    reason: str = Field(..., description="Human-readable conflict explanation")
    current_status: Optional[str] = Field(None, description="Server's current value")


class SyncResponse(BaseModel):
    """Response from sync operation."""
    synced_count: int = Field(..., description="Number of events successfully synced")
    rejected_count: int = Field(..., description="Number of events rejected")
    conflicts: list[SyncConflict] = Field(..., description="List of conflicts encountered")
