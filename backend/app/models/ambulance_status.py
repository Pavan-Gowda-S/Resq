"""
AmbulanceStatus model for fleet tracking of individual emergency ambulances.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from backend.app.database.base import BaseModel


class AmbulanceStatus(BaseModel):
    """
    Fleet tracking of individual emergency ambulances.
    Types: BLS (Basic Life Support), ALS (Advanced Life Support), NEONATAL, PATIENT_TRANSPORT
    Status: AVAILABLE, DISPATCHED, EN_ROUTE, ON_SCENE, PATIENT_ON_BOARD, MAINTENANCE, OFF_DUTY
    """
    __tablename__ = "ambulance_status"

    organization_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="Organization FK"
    )

    vehicle_plate: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Vehicle plate number (unique)"
    )

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Ambulance type: BLS, ALS, NEONATAL, PATIENT_TRANSPORT"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="AVAILABLE",
        comment="Status: AVAILABLE, DISPATCHED, EN_ROUTE, ON_SCENE, PATIENT_ON_BOARD, MAINTENANCE, OFF_DUTY"
    )

    current_location: Mapped[str] = mapped_column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=False,
        comment="Current location (PostGIS POINT)"
    )

    current_task_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("response_tasks.id"),
        nullable=True,
        comment="Current task FK (nullable)"
    )

    last_telemetry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="Last telemetry update timestamp"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="ambulance_status")
    current_task: Mapped[Optional["ResponseTask"]] = relationship("ResponseTask", back_populates="ambulance_status", foreign_keys=[current_task_id])

    def __repr__(self) -> str:
        return f"<AmbulanceStatus(id={self.id}, plate='{self.vehicle_plate}', status='{self.status}')>"
