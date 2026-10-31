"""
ResourceInventory model for disaster relief supplies, medicines, blood reserves, and equipment.
"""
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, Integer, ForeignKey, CheckConstraint, DateTime, Computed
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import BaseModel


class ResourceInventory(BaseModel):
    """
    Disaster relief supplies, medicines, blood reserves, and equipment items.
    Categories: BLOOD_BANK, MEDICAL_SUPPLY, RESCUE_EQUIPMENT, RELIEF_FOOD_WATER
    """
    __tablename__ = "resource_inventory"

    organization_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        comment="Organization FK"
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Category: BLOOD_BANK, MEDICAL_SUPPLY, RESCUE_EQUIPMENT, RELIEF_FOOD_WATER"
    )

    item_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Item code (e.g., BLOOD_O_POS, OXYGEN_CYLINDER_D, INFLATABLE_BOAT_6P)"
    )

    item_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Item name")

    unit: Mapped[str] = mapped_column(String(50), nullable=False, comment="Unit (e.g., units, cylinders, kits)")

    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Total quantity")
    reserved_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", comment="Reserved quantity")

    available_quantity: Mapped[int] = mapped_column(
        Integer,
        Computed("total_quantity - reserved_quantity"),
        comment="Available quantity (generated column)"
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="resource_inventory")

    __table_args__ = (
        CheckConstraint(
            "reserved_quantity <= total_quantity AND total_quantity >= 0 AND reserved_quantity >= 0",
            name="chk_quantity_valid"
        ),
    )

    def __repr__(self) -> str:
        return f"<ResourceInventory(id={self.id}, item='{self.item_code}', available={self.available_quantity})>"
