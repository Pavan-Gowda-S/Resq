"""
Incident model representing canonical emergency incident records.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Text, Integer, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from backend.app.database.base import BaseModel


class Incident(BaseModel):
    """
    Canonical emergency incident records.
    Root entity unifying multiple citizen reports and response tasks.
    """
    __tablename__ = "incidents"

    incident_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="Unique incident number (e.g., RESQ-2026-0041)"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="REPORTED",
        comment="Status: REPORTED, ANALYZING, TRIAGED, DISPATCHING, ACTIVE_RESPONSE, RESOLVED, CLOSED, FALSE_ALARM"
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="MEDIUM",
        comment="Priority: CRITICAL, HIGH, MEDIUM, LOW"
    )

    hazard_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Hazard type: FLOOD, LANDSLIDE, MEDICAL_EMERGENCY, COLLAPSED_STRUCTURE, FIRE, OTHER"
    )

    description: Mapped[str] = mapped_column(Text, nullable=False, comment="Incident description")

    location: Mapped[str] = mapped_column(
        Geography(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=False,
        comment="Geographic location (PostGIS POINT with SRID 4326)"
    )

    district: Mapped[str] = mapped_column(String(100), nullable=False, comment="District")
    landmark: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Nearby landmark")

    people_affected: Mapped[int] = mapped_column(Integer, server_default="1", comment="Number of people affected")
    trapped_count: Mapped[int] = mapped_column(Integer, server_default="0", comment="Number of people trapped")
    injured_count: Mapped[int] = mapped_column(Integer, server_default="0", comment="Number of people injured")

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="UTC timestamp when incident was closed"
    )

    # Relationships
    reports: Mapped[list["IncidentReport"]] = relationship("IncidentReport", back_populates="incident")
    tracking_tokens: Mapped[list["TrackingToken"]] = relationship("TrackingToken", back_populates="incident", cascade="all, delete-orphan")
    tasks: Mapped[list["ResponseTask"]] = relationship("ResponseTask", back_populates="incident", cascade="all, delete-orphan")
    agent_events: Mapped[list["AgentEvent"]] = relationship("AgentEvent", back_populates="incident")

    __table_args__ = (
        Index("idx_incidents_status", "status"),
        Index("idx_incidents_priority", "priority"),
        # GIST index on location created via Geography spatial_index=True
    )

    def __repr__(self) -> str:
        return f"<Incident(id={self.id}, number='{self.incident_number}', status='{self.status}')>"
