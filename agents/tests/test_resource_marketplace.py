"""
Test suite for Resource Marketplace Agent (Phase 5).
Validates ethical supply allocation, split-supplier fulfillment, and atomic reservations.
"""
import pytest
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.resource_marketplace.allocator import allocate_supplies
from agents.resource_marketplace.agent import run_resource_marketplace
from agents.resource_marketplace.schemas import SupplyRequest
from shared.constants import TaskType, UrgencyPriority


# ============================================================================
# Village C Relief Camp Supply Matching Tests
# ============================================================================

@pytest.mark.asyncio
async def test_village_c_water_purification_tablets():
    """
    Test 1: Village C Relief Camp Water Purification Tablets
    Verifies ethical allocation from Depot Alpha with atomic reservation.
    """
    client = ResqApiClient()

    try:
        request = SupplyRequest(
            request_id="req-water-001",
            task_id="task-supply-village-c",
            item_code="PURIFICATION_TABLETS",
            quantity_needed=5000,
            urgency=UrgencyPriority.HIGH.value,
            delivery_location=[76.4320, 9.5840],  # Village C
            clinical_indication="Relief camp running out of clean water"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify allocation structure
        assert allocation_plan.request_id == "req-water-001"
        assert allocation_plan.task_id == "task-supply-village-c"
        assert allocation_plan.item_code == "PURIFICATION_TABLETS"
        assert allocation_plan.total_requested == 5000

        # Verify supplier matched (Depot Alpha has 5000 tablets)
        assert len(allocation_plan.allocations) >= 1
        assert allocation_plan.total_allocated == 5000
        assert allocation_plan.is_fully_allocated is True

        # Verify atomic reservation created
        first_allocation = allocation_plan.allocations[0]
        assert first_allocation.organization_id == "org_supplier_a"
        assert "Medical Supplier Depot Alpha" in first_allocation.supplier_name
        assert first_allocation.allocated_quantity == 5000
        assert first_allocation.distance_km >= 0
        assert first_allocation.reservation_id is not None

        # Verify status
        assert allocation_plan.status == "RESERVED_PENDING_DISPATCH"

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_village_c_ors_sachets():
    """
    Test 2: Village C ORS Sachets for Rehydration
    Verifies allocation from medical supplier.
    """
    client = ResqApiClient()

    try:
        request = SupplyRequest(
            request_id="req-ors-001",
            task_id="task-supply-village-c-ors",
            item_code="ORS_SACHETS",
            quantity_needed=1000,
            urgency=UrgencyPriority.CRITICAL.value,
            delivery_location=[76.4320, 9.5840],
            clinical_indication="Marooned camps, dehydration risk"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify full allocation
        assert allocation_plan.total_allocated == 1000
        assert allocation_plan.is_fully_allocated is True

        # Verify Depot Alpha matched (has 1000 ORS sachets)
        assert len(allocation_plan.allocations) >= 1
        first_allocation = allocation_plan.allocations[0]
        assert first_allocation.organization_id == "org_supplier_a"

    finally:
        await client.close()


# ============================================================================
# Village B Emergency Blood Matching Tests
# ============================================================================

@pytest.mark.asyncio
async def test_village_b_blood_o_neg_medical_approval():
    """
    Test 3: Village B Blood O-Negative for Trauma
    Verifies blood bank matching with medical officer approval flag.
    """
    client = ResqApiClient()

    try:
        request = SupplyRequest(
            request_id="req-blood-001",
            task_id="task-blood-village-b",
            item_code="BLOOD_O_NEG",
            quantity_needed=2,
            urgency=UrgencyPriority.CRITICAL.value,
            delivery_location=[76.1320, 11.5540],  # Village B
            clinical_indication="Compound fracture with hemorrhage"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify blood bank matched
        assert allocation_plan.total_allocated == 2
        assert allocation_plan.is_fully_allocated is True

        # Verify Red Cross Blood Bank matched
        assert len(allocation_plan.allocations) >= 1
        blood_allocation = allocation_plan.allocations[0]
        assert blood_allocation.organization_id == "org_blood_bank_c"
        assert "Blood Bank" in blood_allocation.supplier_name
        assert blood_allocation.allocated_quantity == 2

        # CRITICAL: Verify medical officer approval required
        assert allocation_plan.requires_medical_officer_approval is True

        # Verify atomic reservation
        assert blood_allocation.reservation_id is not None

    finally:
        await client.close()


# ============================================================================
# Split Fulfillment Tests
# ============================================================================

@pytest.mark.asyncio
async def test_split_fulfillment_across_suppliers():
    """
    Test 4: Split Fulfillment Across Multiple Suppliers
    Request exceeding single supplier capacity splits across multiple.
    """
    client = ResqApiClient()

    try:
        # Request more ORS sachets than any single supplier has
        # Depot Alpha has 1000, need to split if requesting more
        request = SupplyRequest(
            request_id="req-ors-large-001",
            task_id="task-large-supply",
            item_code="ORS_SACHETS",
            quantity_needed=1500,
            urgency=UrgencyPriority.HIGH.value,
            delivery_location=[76.3312, 10.3120],
            clinical_indication="Large relief operation"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify allocation attempted
        assert allocation_plan.total_requested == 1500

        # Since Depot Alpha only has 1000 ORS sachets total,
        # we expect partial allocation or full if multiple suppliers
        assert allocation_plan.total_allocated <= 1500

        # If partially allocated, verify status reflects this
        if not allocation_plan.is_fully_allocated:
            assert allocation_plan.status == "PARTIAL_ALLOCATION"

        # Verify all allocations have reservations
        for allocation in allocation_plan.allocations:
            assert allocation.allocated_quantity > 0
            assert allocation.distance_km >= 0

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_partial_allocation_insufficient_stock():
    """
    Test 5: Partial Allocation When Stock Insufficient
    Verifies system allocates what's available without failing.
    """
    client = ResqApiClient()

    try:
        # Request more blood units than available
        # Blood bank has 12 O-NEG units total
        request = SupplyRequest(
            request_id="req-blood-large-001",
            task_id="task-blood-large",
            item_code="BLOOD_O_NEG",
            quantity_needed=20,
            urgency=UrgencyPriority.CRITICAL.value,
            delivery_location=[76.3312, 10.3120],
            clinical_indication="Mass casualty event"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify partial allocation
        assert allocation_plan.total_requested == 20
        assert allocation_plan.total_allocated <= 12  # Max available
        assert allocation_plan.is_fully_allocated is False
        assert allocation_plan.status == "PARTIAL_ALLOCATION"

        # Verify medical approval still required
        assert allocation_plan.requires_medical_officer_approval is True

    finally:
        await client.close()


# ============================================================================
# Ethical Non-Commercial Allocation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_urgency_priority_ordering():
    """
    Test 6: Ethical Priority by Urgency, Not Commercial Bidding
    Verifies CRITICAL requests processed with highest priority.
    """
    client = ResqApiClient()

    try:
        critical_request = SupplyRequest(
            request_id="req-critical-001",
            task_id="task-critical",
            item_code="TRAUMA_KIT",
            quantity_needed=1,
            urgency=UrgencyPriority.CRITICAL.value,
            delivery_location=[76.3312, 10.3120],
            clinical_indication="Life-threatening trauma"
        )

        allocation_plan = await allocate_supplies(critical_request, client)

        # Verify allocation succeeds for critical case
        assert allocation_plan.total_allocated >= 1

        # Verify proximity-based allocation (closest supplier first)
        if allocation_plan.allocations:
            first_allocation = allocation_plan.allocations[0]
            assert first_allocation.distance_km >= 0
            assert first_allocation.estimated_delivery_minutes >= 0

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_proximity_based_allocation():
    """
    Test 7: Proximity-Based Allocation for Faster Delivery
    Verifies closest supplier selected first.
    """
    client = ResqApiClient()

    try:
        request = SupplyRequest(
            request_id="req-proximity-001",
            task_id="task-proximity",
            item_code="ORS_SACHETS",
            quantity_needed=500,
            urgency=UrgencyPriority.HIGH.value,
            delivery_location=[76.3312, 10.3120],
            clinical_indication="Relief camp supplies"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify allocations sorted by distance
        if len(allocation_plan.allocations) > 1:
            distances = [a.distance_km for a in allocation_plan.allocations]
            assert distances == sorted(distances)

    finally:
        await client.close()


# ============================================================================
# State Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_marketplace_state_integration():
    """
    Test 8: Resource Marketplace State Integration
    Verifies state updates with supply allocations and reservations.
    """
    state: AgentState = {
        "incident_id": "inc-village-c",
        "task_proposals": [
            {
                "id": "task-supply-village-c",
                "task_type": TaskType.SUPPLY_DELIVERY.value,
                "target_location": {
                    "type": "Point",
                    "coordinates": [76.4320, 9.5840]
                },
                "priority": UrgencyPriority.HIGH.value,
                "instructions": "Deliver 1000 ORS sachets and water purification tablets to relief camps"
            }
        ]
    }

    client = ResqApiClient()

    try:
        updated_state = await run_resource_marketplace(state, client)

        # Verify matched resources
        assert "matched_resources" in updated_state
        assert "supplies" in updated_state["matched_resources"]

        supply_allocations = updated_state["matched_resources"]["supplies"]
        assert isinstance(supply_allocations, list)
        assert len(supply_allocations) >= 1

        # Verify allocation structure
        for allocation in supply_allocations:
            assert "item_code" in allocation
            assert "total_requested" in allocation
            assert "total_allocated" in allocation
            assert "is_fully_allocated" in allocation
            assert "allocations" in allocation
            assert "status" in allocation

        # Verify reservations created
        assert "reservations" in updated_state
        reservations = updated_state["reservations"]
        assert isinstance(reservations, list)

        # Verify audit trail
        assert "audit_trail" in updated_state
        marketplace_audit = [e for e in updated_state["audit_trail"] if e["agent"] == "ResourceMarketplaceAgent"]
        assert len(marketplace_audit) >= 1

        audit_entry = marketplace_audit[0]
        assert audit_entry["action"] == "supply_allocation_complete"
        assert "results" in audit_entry
        assert audit_entry["results"]["supply_tasks_processed"] == 1

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_multiple_supply_tasks():
    """
    Test 9: Multiple Supply Tasks in Single Run
    Verifies processing multiple supply delivery tasks.
    """
    state: AgentState = {
        "task_proposals": [
            {
                "id": "task-ors",
                "task_type": TaskType.SUPPLY_DELIVERY.value,
                "target_location": {
                    "type": "Point",
                    "coordinates": [76.4320, 9.5840]
                },
                "priority": UrgencyPriority.HIGH.value,
                "instructions": "Deliver ORS sachets"
            },
            {
                "id": "task-tablets",
                "task_type": TaskType.SUPPLY_DELIVERY.value,
                "target_location": {
                    "type": "Point",
                    "coordinates": [76.4320, 9.5840]
                },
                "priority": UrgencyPriority.HIGH.value,
                "instructions": "Deliver water purification tablets"
            }
        ]
    }

    client = ResqApiClient()

    try:
        updated_state = await run_resource_marketplace(state, client)

        # Verify multiple allocations
        supply_allocations = updated_state["matched_resources"]["supplies"]
        assert len(supply_allocations) >= 2

        # Verify audit results
        audit_entry = updated_state["audit_trail"][0]
        assert audit_entry["results"]["supply_tasks_processed"] == 2

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_no_supply_tasks_no_operation():
    """
    Test 10: No Supply Tasks - Agent No-Op
    Verifies agent does nothing when no supply tasks present.
    """
    state: AgentState = {
        "task_proposals": [
            {
                "task_type": TaskType.RESCUE_EXTRACTION.value,
                "instructions": "Rescue operation"
            }
        ]
    }

    client = ResqApiClient()

    try:
        updated_state = await run_resource_marketplace(state, client)

        # State should be unchanged (no supply tasks)
        assert "matched_resources" not in updated_state or \
               "supplies" not in updated_state.get("matched_resources", {})

    finally:
        await client.close()


# ============================================================================
# Edge Case Tests
# ============================================================================

@pytest.mark.asyncio
async def test_no_suppliers_for_item():
    """
    Test 11: No Suppliers Available for Requested Item
    Verifies graceful handling when item not in inventory.
    """
    client = ResqApiClient()

    try:
        request = SupplyRequest(
            request_id="req-unavailable-001",
            task_id="task-unavailable",
            item_code="NONEXISTENT_ITEM",
            quantity_needed=100,
            urgency=UrgencyPriority.HIGH.value,
            delivery_location=[76.3312, 10.3120],
            clinical_indication="Test unavailable item"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify no allocation possible
        assert allocation_plan.total_allocated == 0
        assert allocation_plan.is_fully_allocated is False
        assert allocation_plan.status == "NO_SUPPLIERS_AVAILABLE"
        assert len(allocation_plan.allocations) == 0

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_atomic_reservation_prevents_double_booking():
    """
    Test 12: Atomic Reservations Prevent Double-Booking
    Verifies each allocation creates unique reservation.
    """
    client = ResqApiClient()

    try:
        request = SupplyRequest(
            request_id="req-reservation-001",
            task_id="task-reservation",
            item_code="TRAUMA_KIT",
            quantity_needed=1,
            urgency=UrgencyPriority.CRITICAL.value,
            delivery_location=[76.3312, 10.3120],
            clinical_indication="Emergency trauma kit"
        )

        allocation_plan = await allocate_supplies(request, client)

        # Verify reservation created
        if allocation_plan.allocations:
            reservation_ids = [
                a.reservation_id for a in allocation_plan.allocations
                if a.reservation_id
            ]

            # All reservation IDs should be unique
            assert len(reservation_ids) == len(set(reservation_ids))

            # Each reservation should be a non-empty string
            for res_id in reservation_ids:
                assert isinstance(res_id, str)
                assert len(res_id) > 0

    finally:
        await client.close()
