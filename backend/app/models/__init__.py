"""
SQLAlchemy ORM models for RESQ.
All models are exported here for Alembic autogenerate detection.
"""
from backend.app.database.base import Base, BaseModel

# Import all models to register them with SQLAlchemy metadata
from backend.app.models.organization import Organization
from backend.app.models.user import User
from backend.app.models.incident import Incident
from backend.app.models.incident_report import IncidentReport
from backend.app.models.tracking_token import TrackingToken
from backend.app.models.response_task import ResponseTask
from backend.app.models.hospital_capacity import HospitalCapacity
from backend.app.models.ambulance_status import AmbulanceStatus
from backend.app.models.resource_inventory import ResourceInventory
from backend.app.models.resource_reservation import ResourceReservation
from backend.app.models.status_event import StatusEvent
from backend.app.models.agent_event import AgentEvent
from backend.app.models.audit_log import AuditLog

__all__ = [
    "Base",
    "BaseModel",
    "Organization",
    "User",
    "Incident",
    "IncidentReport",
    "TrackingToken",
    "ResponseTask",
    "HospitalCapacity",
    "AmbulanceStatus",
    "ResourceInventory",
    "ResourceReservation",
    "StatusEvent",
    "AgentEvent",
    "AuditLog",
]

