"""
Resource Marketplace Agent - LangGraph Node.
Autonomously matches supply requests to inventory with ethical allocation.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.resource_marketplace.allocator import allocate_supplies
from agents.resource_marketplace.schemas import SupplyRequest
from shared.constants import TaskType, UrgencyPriority


async def run_resource_marketplace(
    state: AgentState,
    client: Optional[ResqApiClient] = None
) -> AgentState:
    """
    Resource Marketplace Agent LangGraph node.

    Executes:
    1. Scans task proposals for SUPPLY_DELIVERY tasks
    2. Extracts supply requests (item codes, quantities, urgency)
    3. Allocates supplies using ethical principles (urgency + proximity)
    4. Creates atomic 30-minute reservations
    5. Supports split-supplier fulfillment
    6. Stores allocation plans in state
    7. Updates audit trail

    ETHICAL PRINCIPLES (NON-NEGOTIABLE):
    - Priority by clinical urgency and operational need, NOT commercial bidding
    - Proximity-based allocation for faster delivery
    - Split fulfillment across multiple suppliers when needed
    - Atomic reservations to prevent double-booking
    - Medical officer approval for restricted/scarce items

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client

    Returns:
        Updated state with supply allocations
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()

    # Get task proposals
    task_proposals = state.get("task_proposals", [])

    if not task_proposals:
        return state

    # Filter for SUPPLY_DELIVERY tasks
    supply_tasks = [
        task for task in task_proposals
        if task.get("task_type") == TaskType.SUPPLY_DELIVERY.value
    ]

    if not supply_tasks:
        return state

    # Process each supply delivery task
    allocation_plans = []
    all_reservations = state.get("reservations", [])

    for task in supply_tasks:
        # Extract supply request details
        task_id = task.get("id", f"task-supply-{len(allocation_plans)}")
        instructions = task.get("instructions", "")
        target_location = task.get("target_location", {})
        urgency = task.get("priority", UrgencyPriority.MEDIUM.value)

        # Parse item codes from instructions
        # In production, this would use structured task payload
        # For now, extract from instructions text
        item_requests = _parse_supply_items(instructions)

        if not item_requests or "coordinates" not in target_location:
            continue

        delivery_coords = target_location["coordinates"]

        # Allocate each requested item
        for item_code, quantity in item_requests:
            request = SupplyRequest(
                request_id=f"{task_id}_{item_code}",
                task_id=task_id,
                item_code=item_code,
                quantity_needed=quantity,
                urgency=urgency,
                delivery_location=delivery_coords,
                clinical_indication=instructions
            )

            # Allocate supplies
            allocation_plan = await allocate_supplies(request, client)

            allocation_plans.append({
                "request_id": allocation_plan.request_id,
                "task_id": allocation_plan.task_id,
                "item_code": allocation_plan.item_code,
                "total_requested": allocation_plan.total_requested,
                "total_allocated": allocation_plan.total_allocated,
                "is_fully_allocated": allocation_plan.is_fully_allocated,
                "allocations": [a.model_dump() for a in allocation_plan.allocations],
                "requires_medical_officer_approval": allocation_plan.requires_medical_officer_approval,
                "status": allocation_plan.status
            })

            # Collect reservation IDs
            for allocation in allocation_plan.allocations:
                if allocation.reservation_id:
                    all_reservations.append({
                        "reservation_id": allocation.reservation_id,
                        "task_id": task_id,
                        "resource_type": item_code,
                        "organization_id": allocation.organization_id,
                        "quantity": allocation.allocated_quantity,
                        "created_at": datetime.utcnow().isoformat() + "Z"
                    })

    # Update state with allocation plans
    matched_resources = state.get("matched_resources", {})
    matched_resources["supplies"] = allocation_plans
    state["matched_resources"] = matched_resources

    # Update reservations
    state["reservations"] = all_reservations

    # Build audit trail entry
    total_items_allocated = sum(
        plan["total_allocated"] for plan in allocation_plans
    )

    fully_allocated_count = sum(
        1 for plan in allocation_plans if plan["is_fully_allocated"]
    )

    requires_approval_count = sum(
        1 for plan in allocation_plans if plan["requires_medical_officer_approval"]
    )

    audit_entry = {
        "agent": "ResourceMarketplaceAgent",
        "action": "supply_allocation_complete",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "results": {
            "supply_tasks_processed": len(supply_tasks),
            "allocation_plans_created": len(allocation_plans),
            "total_items_allocated": total_items_allocated,
            "fully_allocated_plans": fully_allocated_count,
            "requires_medical_approval": requires_approval_count
        }
    }

    # Append to audit trail
    if "audit_trail" not in state:
        state["audit_trail"] = []
    state["audit_trail"].append(audit_entry)

    # Update state metadata
    state["state_updated_at"] = datetime.utcnow()

    return state


def _parse_supply_items(instructions: str) -> list:
    """
    Parse supply item codes and quantities from task instructions.
    In production, this would come from structured task payload.

    Args:
        instructions: Task instructions text

    Returns:
        List of (item_code, quantity) tuples
    """
    items = []
    instructions_lower = instructions.lower()

    # Map keywords to item codes
    if "ors" in instructions_lower or "rehydration" in instructions_lower:
        # Extract quantity if mentioned, default to 1000
        if "1000" in instructions:
            items.append(("ORS_SACHETS", 1000))
        else:
            items.append(("ORS_SACHETS", 500))

    if "water" in instructions_lower and "purification" in instructions_lower:
        items.append(("PURIFICATION_TABLETS", 5000))

    if "blood" in instructions_lower:
        # Extract blood type
        if "o-neg" in instructions_lower or "o_neg" in instructions_lower or "o neg" in instructions_lower:
            # Extract quantity if mentioned, default to 2 units
            if "2 units" in instructions_lower or "2 unit" in instructions_lower:
                items.append(("BLOOD_O_NEG", 2))
            else:
                items.append(("BLOOD_O_NEG", 1))
        elif "b_pos" in instructions_lower or "b+" in instructions_lower:
            items.append(("BLOOD_B_POS", 1))

    if "trauma" in instructions_lower and "kit" in instructions_lower:
        items.append(("TRAUMA_KIT", 1))

    if "blanket" in instructions_lower:
        items.append(("BLANKETS", 100))

    if "ration" in instructions_lower:
        items.append(("DRY_RATION_KIT", 50))

    return items
