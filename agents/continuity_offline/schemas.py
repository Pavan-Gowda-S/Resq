"""
Continuity & Offline Agent - Data Schemas.
Validated structures for offline event buffering and synchronization.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class OfflineEvent(BaseModel):
    """
    Offline event buffered when network connectivity unavailable.
    UUID-based idempotency ensures duplicate events rejected safely.
    """

    event_id: str = Field(
        ...,
        description="Unique UUIDv4 event identifier for idempotency"
    )

    entity_type: str = Field(
        ...,
        description="Entity type (incident, task, reservation, etc.)"
    )

    entity_id: str = Field(
        ...,
        description="Entity identifier"
    )

    action: str = Field(
        ...,
        description="Action performed (create, update, confirm, etc.)"
    )

    payload: Dict[str, Any] = Field(
        ...,
        description="Event payload data"
    )

    client_timestamp: datetime = Field(
        ...,
        description="Client timestamp when event occurred"
    )

    device_id: str = Field(
        ...,
        description="Device identifier for offline tracking"
    )


class SyncReplayResult(BaseModel):
    """
    Result of offline event synchronization and replay.
    """

    device_id: str = Field(
        ...,
        description="Device identifier"
    )

    total_events: int = Field(
        ...,
        ge=0,
        description="Total events attempted to sync"
    )

    synced_count: int = Field(
        ...,
        ge=0,
        description="Successfully synchronized events"
    )

    rejected_count: int = Field(
        ...,
        ge=0,
        description="Rejected events (duplicates or conflicts)"
    )

    conflicts: List[str] = Field(
        default_factory=list,
        description="Conflict descriptions for rejected events"
    )

    replay_status: str = Field(
        ...,
        description="Overall replay status (SUCCESS, PARTIAL, FAILED)"
    )
