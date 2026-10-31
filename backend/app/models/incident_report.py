"""
IncidentReport model for individual citizen reports linking to incidents.
"""
from typing import Optional
from uuid import UUID as UUID_Type

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from backend.app.database.base import BaseModel


class IncidentReport(BaseModel):
    """
    Individual reports received from citizens, observers, or emergency calls linking to an incident.
    """
    __tablename__ = "incident_reports"

    incident_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Incident FK (initially null, linked after triage)"
    )

    reporter_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Reporter name (anonymous allowed)"
    )

    reporter_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Reporter phone")

    raw_text: Mapped[str] = mapped_column(Text, nullable=False, comment="Raw report text from citizen")

    reported_location: Mapped[Optional[str]] = mapped_column(
        Geography(geometry_type='POINT', srid=4326),
        nullable=True,
        comment="Reported location (PostGIS POINT)"
    )

    reported_landmark: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Reported landmark")

    source: Mapped[str] = mapped_column(
        String(50),
        server_default="WEB_ANONYMOUS",
        comment="Report source: WEB_ANONYMOUS, PWA_OFFLINE_SYNC, CALL_CENTER, SMS_GATEWAY"
    )

    extracted_entities: Mapped[dict] = mapped_column(
        JSONB,
        server_default="{}",
        comment="AI-extracted entities from raw text"
    )

    # Relationships
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="reports")

    def __repr__(self) -> str:
        return f"<IncidentReport(id={self.id}, incident_id={self.incident_id}, source='{self.source}')>"
