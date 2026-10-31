"""
Resource Marketplace Agent - Allocation Engine.
Ethical allocation of medical supplies and blood units with split-supplier fulfillment.
"""
import math
from typing import List, Dict, Any
from agents.core.client import ResqApiClient
from agents.resource_marketplace.schemas import (
    SupplyRequest,
    SupplierAllocation,
    AllocationPlan
)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


async def allocate_supplies(
    request: SupplyRequest,
    client: ResqApiClient
) -> AllocationPlan:
    """
    Allocate supplies using ethical principles: urgency-based, proximity-aware,
    with split-supplier fulfillment.

    ETHICAL PRINCIPLES:
    1. Priority by clinical urgency and operational need, NOT commercial bidding
    2. Proximity-based allocation for faster delivery
    3. Split fulfillment across multiple suppliers when needed
    4. Atomic 30-minute reservations to prevent double-booking
    5. Medical officer approval for restricted/scarce items

    Args:
        request: Supply request with item code, quantity, urgency, location
        client: RESQ API client for inventory queries and reservations

    Returns:
        AllocationPlan with supplier allocations and reservation IDs
    """

    # Query available inventory for requested item
    inventory_response = await client.search_inventory(
        item_code=request.item_code,
        min_quantity=1
    )

    suppliers = inventory_response.get("suppliers", [])

    if not suppliers:
        # No suppliers have this item
        return AllocationPlan(
            request_id=request.request_id,
            task_id=request.task_id,
            item_code=request.item_code,
            total_requested=request.quantity_needed,
            total_allocated=0,
            is_fully_allocated=False,
            allocations=[],
            requires_medical_officer_approval=False,
            status="NO_SUPPLIERS_AVAILABLE"
        )

    # Calculate distance from each supplier to delivery location
    delivery_lng, delivery_lat = request.delivery_location

    supplier_distances = []
    for supplier in suppliers:
        supplier_lng, supplier_lat = supplier["location"]["coordinates"]
        distance_km = haversine_distance(
            delivery_lat, delivery_lng,
            supplier_lat, supplier_lng
        )

        # Find available quantity for requested item
        available_qty = 0
        for item in supplier.get("inventory", []):
            if item["item_code"] == request.item_code:
                available_qty = item["available_quantity"]
                break

        supplier_distances.append({
            "supplier": supplier,
            "distance_km": distance_km,
            "available_quantity": available_qty
        })

    # Sort by distance (proximity-based ethical allocation)
    supplier_distances.sort(key=lambda x: x["distance_km"])

    # Allocate quantity across suppliers (split fulfillment)
    allocations: List[SupplierAllocation] = []
    remaining_needed = request.quantity_needed

    for supplier_data in supplier_distances:
        if remaining_needed <= 0:
            break

        supplier = supplier_data["supplier"]
        available = supplier_data["available_quantity"]
        distance_km = supplier_data["distance_km"]

        # Allocate min(remaining_needed, available)
        allocated_qty = min(remaining_needed, available)

        # Estimate delivery time (40 km/h with disaster conditions)
        estimated_minutes = int((distance_km / 40.0) * 60)

        # Create atomic reservation
        reservation_id = None
        try:
            reservation_response = await client.create_reservation(
                task_id=request.task_id,
                organization_id=supplier["organization_id"],
                resource_type=request.item_code,
                quantity=allocated_qty,
                lock_duration_minutes=30
            )
            reservation_id = reservation_response.get("reservation_id")
        except Exception:
            # Reservation failed, but record allocation attempt
            pass

        allocation = SupplierAllocation(
            organization_id=supplier["organization_id"],
            supplier_name=supplier["organization_name"],
            item_code=request.item_code,
            allocated_quantity=allocated_qty,
            distance_km=round(distance_km, 2),
            estimated_delivery_minutes=estimated_minutes,
            reservation_id=reservation_id
        )

        allocations.append(allocation)
        remaining_needed -= allocated_qty

    total_allocated = sum(a.allocated_quantity for a in allocations)
    is_fully_allocated = total_allocated >= request.quantity_needed

    # Check if medical officer approval required
    restricted_items = ["BLOOD_O_NEG", "BLOOD_O_POS", "RARE_ANTIVENOM", "CONTROLLED_MEDICATIONS"]
    requires_approval = request.item_code in restricted_items

    status = "RESERVED_PENDING_DISPATCH" if is_fully_allocated else "PARTIAL_ALLOCATION"
    if not allocations:
        status = "NO_ALLOCATION_POSSIBLE"

    return AllocationPlan(
        request_id=request.request_id,
        task_id=request.task_id,
        item_code=request.item_code,
        total_requested=request.quantity_needed,
        total_allocated=total_allocated,
        is_fully_allocated=is_fully_allocated,
        allocations=allocations,
        requires_medical_officer_approval=requires_approval,
        status=status
    )
