"""
ResponseTask model for discrete executable tasks spawned by incidents.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, Text, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from backend.app.database.base import BaseModel


class ResponseTask(BaseModel):
    """
    Discrete executable tasks spawned by an incident.
    One incident can have many linked tasks (e.g., rescue + ambulance + hospital admission).
    """
    __tablename__ = "response_tasks"

    incident_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Incident FK"
    )

    parent_task_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("response_tasks.id"),
        nullable=True,
        comment="Parent task FK for task dependency chains"
    )

    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Task type: RESCUE_EXTRACTION, AMBULANCE_TRANSPORT, HOSPITAL_ADMISSION, SUPPLY_DELIVERY, RELIEF_CAMP_SHELTER"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="PENDING_ASSIGNMENT",
        comment="Status: PENDING_ASSIGNMENT, ASSIGNED, ACCEPTED, REJECTED, EN_ROUTE, ON_SCENE, COMPLETED, CANCELLED"
    )

    priority: Mapped[str] = mapped_column(String(20), nullable=False, comment="Priority: CRITICAL, HIGH, MEDIUM, LOW")

    assigned_organization_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        comment="Assigned organization FK"
    )

    assigned_user_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        comment="Assigned responder FK"
    )

    target_location: Mapped[str] = mapped_column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=False,
        comment="Target location (PostGIS POINT)"
    )

    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Task instructions")

    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    citizen_confirmed_arrival: Mapped[bool] = mapped_column(Boolean, server_default="false", comment="Citizen arrival confirmation")
    citizen_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="tasks")
    assigned_organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="response_tasks", foreign_keys=[assigned_organization_id])
    assigned_user: Mapped[Optional["User"]] = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_user_id])
    parent_task: Mapped[Optional["ResponseTask"]] = relationship("ResponseTask", remote_side="ResponseTask.id", foreign_keys=[parent_task_id])
    child_tasks: Mapped[list["ResponseTask"]] = relationship("ResponseTask", back_populates="parent_task", foreign_keys=[parent_task_id])
    resource_reservations: Mapped[list["ResourceReservation"]] = relationship("ResourceReservation", back_populates="task", cascade="all, delete-orphan")
    ambulance_status: Mapped[Optional["AmbulanceStatus"]] = relationship("AmbulanceStatus", back_populates="current_task", foreign_keys="AmbulanceStatus.current_task_id")

    __table_args__ = (
        Index("idx_tasks_incident", "incident_id"),
        Index("idx_tasks_status", "status"),
        Index("idx_tasks_assigned_org", "assigned_organization_id"),
    )

    def __repr__(self) -> str:
        return f"<ResponseTask(id={self.id}, type='{self.task_type}', status='{self.status}')>"
