"""
Reservation service: Atomic resource locking and capacity management.
"""
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.app.models import (
    ResourceReservation,
    HospitalCapacity,
    ResourceInventory,
    AmbulanceStatus,
    ResponseTask
)


async def create_reservation(
    db: AsyncSession,
    task_id: UUID,
    organization_id: UUID,
    resource_type: str,
    quantity: int,
    lock_duration_minutes: int = 30,
    item_code: Optional[str] = None
) -> ResourceReservation:
    """
    Create atomic resource reservation with capacity verification.

    This function operates in a single database transaction:
    1. Verifies available capacity >= requested quantity
    2. Increments reserved count in capacity table
    3. Creates ResourceReservation with status HOLD
    4. Raises 400 RESOURCE_INSUFFICIENT if capacity cannot satisfy request

    Args:
        db: Database session
        task_id: Task requesting the resource
        organization_id: Organization providing the resource
        resource_type: Type of resource (HOSPITAL_EMERGENCY_BED, HOSPITAL_ICU_BED, etc.)
        quantity: Number of units to reserve
        lock_duration_minutes: Duration before reservation expires
        item_code: Required for inventory items

    Returns:
        Created ResourceReservation

    Raises:
        HTTPException 400: Insufficient capacity
        HTTPException 404: Resource not found
    """
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=lock_duration_minutes)
    resource_id = None  # Initialize for non-inventory resources

    # Handle different resource types
    if resource_type == "HOSPITAL_EMERGENCY_BED":
        # Get hospital capacity with row lock
        result = await db.execute(
            select(HospitalCapacity)
            .where(HospitalCapacity.organization_id == organization_id)
            .with_for_update()
        )
        capacity = result.scalar_one_or_none()

        if not capacity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hospital capacity record not found"
            )

        # Calculate available beds
        available = (
            capacity.total_emergency_beds -
            capacity.occupied_emergency_beds -
            capacity.reserved_emergency_beds -
            capacity.out_of_service_emergency_beds
        )

        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RESOURCE_INSUFFICIENT: Only {available} emergency beds available, requested {quantity}"
            )

        # Increment reserved count
        capacity.reserved_emergency_beds += quantity

    elif resource_type == "HOSPITAL_ICU_BED":
        # Get hospital capacity with row lock
        result = await db.execute(
            select(HospitalCapacity)
            .where(HospitalCapacity.organization_id == organization_id)
            .with_for_update()
        )
        capacity = result.scalar_one_or_none()

        if not capacity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hospital capacity record not found"
            )

        # Calculate available ICU beds
        available = (
            capacity.total_icu_beds -
            capacity.occupied_icu_beds -
            capacity.reserved_icu_beds -
            capacity.out_of_service_icu_beds
        )

        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RESOURCE_INSUFFICIENT: Only {available} ICU beds available, requested {quantity}"
            )

        # Increment reserved count
        capacity.reserved_icu_beds += quantity

    elif resource_type in ["MEDICAL_SUPPLY", "RELIEF_MATERIAL", "EQUIPMENT", "FOOD_WATER"]:
        # Get inventory item with row lock
        if not item_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="item_code is required for inventory reservations"
            )

        result = await db.execute(
            select(ResourceInventory)
            .where(
                and_(
                    ResourceInventory.organization_id == organization_id,
                    ResourceInventory.item_code == item_code
                )
            )
            .with_for_update()
        )
        inventory = result.scalar_one_or_none()

        if not inventory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory item {item_code} not found"
            )

        # Calculate available quantity
        available = inventory.total_quantity - inventory.reserved_quantity

        if available < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"RESOURCE_INSUFFICIENT: Only {available} units available, requested {quantity}"
            )

        # Increment reserved count
        inventory.reserved_quantity += quantity

        # Store inventory ID in resource_id field
        resource_id = inventory.id

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported resource_type: {resource_type}"
        )

    # Create reservation record (with resource_id for inventory items)
    reservation = ResourceReservation(
        task_id=task_id,
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id if resource_type in ["MEDICAL_SUPPLY", "RELIEF_MATERIAL", "EQUIPMENT", "FOOD_WATER"] else None,
        quantity=quantity,
        status="HOLD",
        expires_at=expires_at,
    )

    db.add(reservation)
    await db.flush()

    return reservation


async def fulfill_reservation(
    db: AsyncSession,
    reservation_id: UUID,
    notes: Optional[str] = None
) -> ResourceReservation:
    """
    Fulfill a reservation by moving from HOLD to CONFIRMED_FULFILLED.

    For bed reservations, moves count from reserved to occupied.
    For inventory, keeps the reserved count (will be decremented on task completion).

    Args:
        db: Database session
        reservation_id: Reservation to fulfill
        notes: Optional fulfillment notes

    Returns:
        Updated ResourceReservation

    Raises:
        HTTPException 404: Reservation not found
        HTTPException 400: Invalid status for fulfillment
    """
    # Get reservation with lock
    result = await db.execute(
        select(ResourceReservation)
        .where(ResourceReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )

    if reservation.status != "HOLD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fulfill reservation with status {reservation.status}"
        )

    # Check if expired
    if reservation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reservation has expired"
        )

    # Handle bed reservations - move from reserved to occupied
    if reservation.resource_type == "HOSPITAL_EMERGENCY_BED":
        result = await db.execute(
            select(HospitalCapacity)
            .where(HospitalCapacity.organization_id == reservation.organization_id)
            .with_for_update()
        )
        capacity = result.scalar_one_or_none()

        if capacity:
            capacity.reserved_emergency_beds -= reservation.quantity
            capacity.occupied_emergency_beds += reservation.quantity

    elif reservation.resource_type == "HOSPITAL_ICU_BED":
        result = await db.execute(
            select(HospitalCapacity)
            .where(HospitalCapacity.organization_id == reservation.organization_id)
            .with_for_update()
        )
        capacity = result.scalar_one_or_none()

        if capacity:
            capacity.reserved_icu_beds -= reservation.quantity
            capacity.occupied_icu_beds += reservation.quantity

    # Update reservation status
    reservation.status = "CONFIRMED_FULFILLED"

    return reservation


async def release_reservation(
    db: AsyncSession,
    reservation_id: UUID,
    reason: Optional[str] = None
) -> ResourceReservation:
    """
    Release a reservation, restoring capacity.

    Args:
        db: Database session
        reservation_id: Reservation to release
        reason: Optional release reason

    Returns:
        Updated ResourceReservation

    Raises:
        HTTPException 404: Reservation not found
    """
    # Get reservation with lock
    result = await db.execute(
        select(ResourceReservation)
        .where(ResourceReservation.id == reservation_id)
        .with_for_update()
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )

    # Only release if currently on HOLD
    if reservation.status != "HOLD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot release reservation with status {reservation.status}"
        )

    # Restore capacity based on resource type
    if reservation.resource_type == "HOSPITAL_EMERGENCY_BED":
        result = await db.execute(
            select(HospitalCapacity)
            .where(HospitalCapacity.organization_id == reservation.organization_id)
            .with_for_update()
        )
        capacity = result.scalar_one_or_none()

        if capacity:
            capacity.reserved_emergency_beds -= reservation.quantity

    elif reservation.resource_type == "HOSPITAL_ICU_BED":
        result = await db.execute(
            select(HospitalCapacity)
            .where(HospitalCapacity.organization_id == reservation.organization_id)
            .with_for_update()
        )
        capacity = result.scalar_one_or_none()

        if capacity:
            capacity.reserved_icu_beds -= reservation.quantity

    elif reservation.resource_type in ["MEDICAL_SUPPLY", "RELIEF_MATERIAL", "EQUIPMENT", "FOOD_WATER"]:
        if reservation.resource_id:
            result = await db.execute(
                select(ResourceInventory)
                .where(ResourceInventory.id == reservation.resource_id)
                .with_for_update()
            )
            inventory = result.scalar_one_or_none()

            if inventory:
                inventory.reserved_quantity -= reservation.quantity

    # Update reservation status
    reservation.status = "RELEASED"

    return reservation


async def expire_stale_reservations(db: AsyncSession) -> int:
    """
    Background sweep to expire all stale HOLD reservations and restore capacity.

    This should be called periodically (e.g., every 5 minutes) to ensure
    expired reservations don't block capacity indefinitely.

    Args:
        db: Database session

    Returns:
        Number of reservations expired
    """
    now = datetime.now(timezone.utc)

    # Find all expired HOLD reservations
    result = await db.execute(
        select(ResourceReservation)
        .where(
            and_(
                ResourceReservation.status == "HOLD",
                ResourceReservation.expires_at < now
            )
        )
        .with_for_update()
    )
    expired_reservations = result.scalars().all()

    count = 0

    for reservation in expired_reservations:
        # Restore capacity
        if reservation.resource_type == "HOSPITAL_EMERGENCY_BED":
            result = await db.execute(
                select(HospitalCapacity)
                .where(HospitalCapacity.organization_id == reservation.organization_id)
                .with_for_update()
            )
            capacity = result.scalar_one_or_none()

            if capacity and capacity.reserved_emergency_beds >= reservation.quantity:
                capacity.reserved_emergency_beds -= reservation.quantity

        elif reservation.resource_type == "HOSPITAL_ICU_BED":
            result = await db.execute(
                select(HospitalCapacity)
                .where(HospitalCapacity.organization_id == reservation.organization_id)
                .with_for_update()
            )
            capacity = result.scalar_one_or_none()

            if capacity and capacity.reserved_icu_beds >= reservation.quantity:
                capacity.reserved_icu_beds -= reservation.quantity

        elif reservation.resource_type in ["MEDICAL_SUPPLY", "RELIEF_MATERIAL", "EQUIPMENT", "FOOD_WATER"]:
            if reservation.item_code:
                result = await db.execute(
                    select(ResourceInventory)
                    .where(
                        and_(
                            ResourceInventory.organization_id == reservation.organization_id,
                            ResourceInventory.item_code == reservation.item_code
                        )
                    )
                    .with_for_update()
                )
                inventory = result.scalar_one_or_none()

                if inventory and inventory.reserved_quantity >= reservation.quantity:
                    inventory.reserved_quantity -= reservation.quantity

        # Mark as expired
        reservation.status = "EXPIRED"
        count += 1

    return count
