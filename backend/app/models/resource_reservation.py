"""
ResourceReservation model for time-bounded locks on resources.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import BaseModel


class ResourceReservation(BaseModel):
    """
    Time-bounded locks on resources (beds, blood units, gear) during dispatch coordination.
    Resource types: HOSPITAL_EMERGENCY_BED, HOSPITAL_ICU_BED, INVENTORY_ITEM
    Status: HOLD, CONFIRMED_FULFILLED, RELEASED_EXPIRED, CANCELLED
    """
    __tablename__ = "resource_reservations"

    task_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("response_tasks.id", ondelete="CASCADE"),
        nullable=False,
        comment="Task FK"
    )

    organization_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        comment="Organization FK"
    )

    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Resource type: HOSPITAL_EMERGENCY_BED, HOSPITAL_ICU_BED, INVENTORY_ITEM"
    )

    resource_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Resource ID (e.g., resource_inventory.id when applicable)"
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1", comment="Quantity reserved")

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default="HOLD",
        comment="Status: HOLD, CONFIRMED_FULFILLED, RELEASED_EXPIRED, CANCELLED"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Reservation expiration timestamp (typically NOW() + 30 minutes)"
    )

    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fulfillment timestamp"
    )

    # Relationships
    task: Mapped["ResponseTask"] = relationship("ResponseTask", back_populates="resource_reservations")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="resource_reservations")

    def __repr__(self) -> str:
        return f"<ResourceReservation(id={self.id}, type='{self.resource_type}', status='{self.status}')>"
