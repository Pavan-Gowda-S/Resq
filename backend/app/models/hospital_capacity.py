"""
HospitalCapacity model for deterministic hospital bed and trauma room availability.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import Integer, Boolean, ForeignKey, CheckConstraint, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class HospitalCapacity(Base):
    """
    Deterministic hospital bed and trauma room availability.
    Enforces capacity invariants: occupied + reserved + out_of_service <= total
    """
    __tablename__ = "hospital_capacity"

    id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
        comment="Primary key (UUIDv4)"
    )

    organization_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="Organization FK (unique, one-to-one)"
    )

    # Emergency Beds
    total_emergency_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Total emergency beds")
    occupied_emergency_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Occupied emergency beds")
    reserved_emergency_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Reserved emergency beds")
    out_of_service_emergency_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Out-of-service emergency beds")

    # ICU Beds
    total_icu_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Total ICU beds")
    occupied_icu_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Occupied ICU beds")
    reserved_icu_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Reserved ICU beds")
    out_of_service_icu_beds: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Out-of-service ICU beds")

    # Facilities
    has_oxygen_facility: Mapped[bool] = mapped_column(Boolean, server_default="true", comment="Oxygen facility available")
    has_trauma_center: Mapped[bool] = mapped_column(Boolean, server_default="true", comment="Trauma center available")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Last update timestamp"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="hospital_capacity")

    __table_args__ = (
        CheckConstraint(
            "occupied_emergency_beds + reserved_emergency_beds + out_of_service_emergency_beds <= total_emergency_beds",
            name="chk_emergency_beds"
        ),
        CheckConstraint(
            "occupied_icu_beds + reserved_icu_beds + out_of_service_icu_beds <= total_icu_beds",
            name="chk_icu_beds"
        ),
    )

    def __repr__(self) -> str:
        return f"<HospitalCapacity(id={self.id}, org={self.organization_id})>"
