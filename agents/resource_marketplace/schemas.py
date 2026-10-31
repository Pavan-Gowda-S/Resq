"""
Resource Marketplace Agent - Data Schemas.
Validated structures for supply requests, allocations, and fulfillment tracking.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from shared.constants import UrgencyPriority


class SupplyRequest(BaseModel):
    """
    Request for medical supplies or blood units from relief operations.
    """

    request_id: str = Field(
        ...,
        description="Unique request identifier"
    )

    task_id: str = Field(
        ...,
        description="Associated task ID from task proposals"
    )

    item_code: str = Field(
        ...,
        description="Item code (e.g. ORS_SACHETS, BLOOD_O_NEG, TRAUMA_KIT)"
    )

    quantity_needed: int = Field(
        ...,
        ge=1,
        description="Quantity required"
    )

    urgency: str = Field(
        ...,
        description="Urgency priority (CRITICAL, HIGH, MEDIUM, LOW)"
    )

    delivery_location: List[float] = Field(
        ...,
        description="Delivery coordinates [longitude, latitude]"
    )

    clinical_indication: Optional[str] = Field(
        default=None,
        description="Clinical reason for request (e.g. 'compound fracture trauma')"
    )


class SupplierAllocation(BaseModel):
    """
    Allocation of supplies from a specific supplier organization.
    """

    organization_id: str = Field(
        ...,
        description="Supplier organization ID"
    )

    supplier_name: str = Field(
        ...,
        description="Supplier organization name"
    )

    item_code: str = Field(
        ...,
        description="Item code being allocated"
    )

    allocated_quantity: int = Field(
        ...,
        ge=1,
        description="Quantity allocated from this supplier"
    )

    distance_km: float = Field(
        ...,
        ge=0.0,
        description="Distance from supplier to delivery location"
    )

    estimated_delivery_minutes: int = Field(
        ...,
        ge=0,
        description="Estimated delivery time in minutes"
    )

    reservation_id: Optional[str] = Field(
        default=None,
        description="Atomic reservation ID (30-minute lock)"
    )


class AllocationPlan(BaseModel):
    """
    Complete allocation plan for a supply request, potentially split across suppliers.
    """

    request_id: str = Field(
        ...,
        description="Original request ID"
    )

    task_id: str = Field(
        ...,
        description="Associated task ID"
    )

    item_code: str = Field(
        ...,
        description="Item code being allocated"
    )

    total_requested: int = Field(
        ...,
        ge=1,
        description="Total quantity requested"
    )

    total_allocated: int = Field(
        ...,
        ge=0,
        description="Total quantity successfully allocated"
    )

    is_fully_allocated: bool = Field(
        ...,
        description="Whether request is fully satisfied"
    )

    allocations: List[SupplierAllocation] = Field(
        default_factory=list,
        description="List of supplier allocations"
    )

    requires_medical_officer_approval: bool = Field(
        default=False,
        description="Whether restricted/scarce items need approval"
    )

    status: str = Field(
        ...,
        description="Allocation status (RESERVED_PENDING_DISPATCH, PARTIAL, etc.)"
    )


class FulfilmentRecord(BaseModel):
    """
    Tracking record for supply delivery logistics.
    """

    allocation_plan_id: str = Field(
        ...,
        description="Reference to allocation plan"
    )

    courier_task_id: Optional[str] = Field(
        default=None,
        description="Courier/delivery task ID"
    )

    dispatch_status: str = Field(
        ...,
        description="Dispatch status (PENDING, IN_TRANSIT, DELIVERED)"
    )

    dispatched_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when dispatched"
    )

    delivered_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when delivered"
    )
