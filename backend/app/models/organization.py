"""
Organization model representing registered emergency network entities.
"""
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geography

from backend.app.database.base import BaseModel


class Organization(BaseModel):
    """
    Represents registered legal/operational entities participating in the emergency network.
    Types: RESCUE, HOSPITAL, AMBULANCE_PROVIDER, PHARMACY, BLOOD_BANK, SUPPLIER, CONTROL_ROOM, ADMIN
    """
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Organization name")

    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Organization type: RESCUE, HOSPITAL, AMBULANCE_PROVIDER, PHARMACY, BLOOD_BANK, SUPPLIER, CONTROL_ROOM, ADMIN"
    )

    registration_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        comment="Official registration number"
    )

    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default="PENDING",
        comment="Verification status: PENDING, VERIFIED, SUSPENDED"
    )

    contact_email: Mapped[str] = mapped_column(String(255), nullable=False, comment="Primary contact email")
    contact_phone: Mapped[str] = mapped_column(String(50), nullable=False, comment="Primary contact phone")

    location: Mapped[str] = mapped_column(
        Geography(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=False,
        comment="Geographic location (PostGIS POINT with SRID 4326)"
    )

    address: Mapped[str] = mapped_column(Text, nullable=False, comment="Full address")
    district: Mapped[str] = mapped_column(String(100), nullable=False, comment="District (e.g., Ernakulam, Wayanad)")

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    response_tasks: Mapped[list["ResponseTask"]] = relationship("ResponseTask", back_populates="assigned_organization", foreign_keys="ResponseTask.assigned_organization_id")
    hospital_capacity: Mapped[Optional["HospitalCapacity"]] = relationship("HospitalCapacity", back_populates="organization", uselist=False, cascade="all, delete-orphan")
    ambulance_status: Mapped[list["AmbulanceStatus"]] = relationship("AmbulanceStatus", back_populates="organization", cascade="all, delete-orphan")
    resource_inventory: Mapped[list["ResourceInventory"]] = relationship("ResourceInventory", back_populates="organization", cascade="all, delete-orphan")
    resource_reservations: Mapped[list["ResourceReservation"]] = relationship("ResourceReservation", back_populates="organization")

    __table_args__ = (
        Index("idx_org_type", "type"),
        Index("idx_org_verification", "verification_status"),
        # GIST index on location is created via Geography spatial_index=True
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, name='{self.name}', type='{self.type}')>"
