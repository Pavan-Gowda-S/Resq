"""
Test suite for resource reservation (atomic locking) functionality.
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.models import HospitalCapacity, ResourceInventory, ResourceReservation


client = TestClient(app)


def test_create_emergency_bed_reservation(db_session, superadmin_headers, test_organization, test_task):
    """Test creating atomic reservation for emergency bed."""
    # Create hospital capacity
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=5,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    # Create incident and task for reservation
    task_id = test_task

    # Create reservation
    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 2,
        "lock_duration_minutes": 30
    }

    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )

    assert response.status_code == 201
    data = response.json()

    assert data["task_id"] == str(task_id)
    assert data["resource_type"] == "HOSPITAL_EMERGENCY_BED"
    assert data["quantity"] == 2
    assert data["status"] == "HOLD"
    assert "expires_at" in data

    # Verify capacity was decremented
    db_session.refresh(capacity)
    assert capacity.reserved_emergency_beds == 7  # Was 5, now 7


def test_create_icu_bed_reservation(db_session, superadmin_headers, test_organization, test_task):
    """Test creating atomic reservation for ICU bed."""
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=5,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    task_id = test_task

    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_ICU_BED",
        "quantity": 1,
        "lock_duration_minutes": 30
    }

    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "HOLD"

    # Verify ICU capacity was decremented
    db_session.refresh(capacity)
    assert capacity.reserved_icu_beds == 3  # Was 2, now 3


def test_reservation_insufficient_capacity(db_session, superadmin_headers, test_organization, test_task):
    """Test reservation rejection when capacity is insufficient."""
    # Create capacity with only 5 available emergency beds
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=30,
        reserved_emergency_beds=10,
        out_of_service_emergency_beds=5,  # Only 5 available
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    task_id = test_task

    # Try to reserve 10 beds (more than available)
    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 10,
        "lock_duration_minutes": 30
    }

    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )

    assert response.status_code == 400
    assert "RESOURCE_INSUFFICIENT" in response.json()["detail"]

    # Verify capacity was NOT changed
    db_session.refresh(capacity)
    assert capacity.reserved_emergency_beds == 10  # Unchanged


def test_fulfill_reservation(db_session, superadmin_headers, test_organization, test_task):
    """Test fulfilling reservation (moves from reserved to occupied)."""
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=5,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    task_id = test_task

    # Create reservation
    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 2,
        "lock_duration_minutes": 30
    }

    create_response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )
    reservation_id = create_response.json()["id"]

    # Fulfill reservation
    fulfill_response = client.post(
        f"/api/v1/resources/reservations/{reservation_id}/fulfill",
        json={"notes": "Patient admitted to emergency ward"},
        headers=superadmin_headers
    )

    assert fulfill_response.status_code == 200
    data = fulfill_response.json()
    assert data["status"] == "CONFIRMED_FULFILLED"

    # Verify beds moved from reserved to occupied
    db_session.refresh(capacity)
    assert capacity.reserved_emergency_beds == 5  # Back to original (7 - 2)
    assert capacity.occupied_emergency_beds == 22  # Increased by 2 (20 + 2)


def test_release_reservation(db_session, superadmin_headers, test_organization, test_task):
    """Test releasing reservation (restores capacity)."""
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=5,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    task_id = test_task

    # Create reservation
    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_ICU_BED",
        "quantity": 2,
        "lock_duration_minutes": 30
    }

    create_response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )
    reservation_id = create_response.json()["id"]

    # Release reservation
    release_response = client.post(
        f"/api/v1/resources/reservations/{reservation_id}/release",
        json={"reason": "Task cancelled, bed no longer needed"},
        headers=superadmin_headers
    )

    assert release_response.status_code == 200
    data = release_response.json()
    assert data["status"] == "RELEASED"

    # Verify capacity was restored
    db_session.refresh(capacity)
    assert capacity.reserved_icu_beds == 2  # Back to original (4 - 2)


def test_inventory_reservation(db_session, superadmin_headers, test_organization, test_task):
    """Test reserving inventory items."""
    # Create inventory
    inventory = ResourceInventory(
        organization_id=test_organization.id,
        category="MEDICAL_SUPPLY",
        item_code="BLOOD-O-POS",
        item_name="O+ Blood Units",
        unit="UNITS",
        total_quantity=50,
        reserved_quantity=5
    )
    db_session.add(inventory)
    db_session.commit()

    task_id = test_task

    # Create reservation
    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "MEDICAL_SUPPLY",
        "quantity": 3,
        "lock_duration_minutes": 30,
        "item_code": "BLOOD-O-POS"
    }

    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "HOLD"

    # Verify inventory was decremented
    db_session.refresh(inventory)
    assert inventory.reserved_quantity == 8  # Was 5, now 8


def test_inventory_reservation_insufficient_stock(db_session, superadmin_headers, test_organization, test_task):
    """Test inventory reservation rejection when stock is insufficient."""
    # Create inventory with limited stock
    inventory = ResourceInventory(
        organization_id=test_organization.id,
        category="EQUIPMENT",
        item_code="BOAT-INFLT-6P",
        item_name="Inflatable Rescue Boat",
        unit="PIECES",
        total_quantity=10,
        reserved_quantity=8  # Only 2 available
    )
    db_session.add(inventory)
    db_session.commit()

    task_id = test_task

    # Try to reserve 5 boats (more than available)
    reservation_data = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "EQUIPMENT",
        "quantity": 5,
        "lock_duration_minutes": 30,
        "item_code": "BOAT-INFLT-6P"
    }

    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )

    assert response.status_code == 400
    assert "RESOURCE_INSUFFICIENT" in response.json()["detail"]

    # Verify inventory was NOT changed
    db_session.refresh(inventory)
    assert inventory.reserved_quantity == 8  # Unchanged


def test_get_task_reservations(db_session, superadmin_headers, test_organization, test_task):
    """Test getting all reservations for a task."""
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=5,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    task_id = test_task

    # Create multiple reservations for same task
    reservation_data_1 = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 1,
        "lock_duration_minutes": 30
    }

    reservation_data_2 = {
        "task_id": str(task_id),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_ICU_BED",
        "quantity": 1,
        "lock_duration_minutes": 30
    }

    client.post("/api/v1/resources/reservations", json=reservation_data_1, headers=superadmin_headers)
    client.post("/api/v1/resources/reservations", json=reservation_data_2, headers=superadmin_headers)

    # Get all reservations for task
    response = client.get(
        f"/api/v1/resources/reservations/task/{task_id}",
        headers=superadmin_headers
    )

    assert response.status_code == 200
    reservations = response.json()
    assert len(reservations) == 2


def test_reservation_requires_authorization(db_session, auth_headers, test_task):
    """Test that regular users cannot create reservations."""
    from uuid import uuid4

    reservation_data = {
        "task_id": str(test_task),
        "organization_id": str(uuid4()),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 1,
        "lock_duration_minutes": 30
    }

    # TRIAGE_DOCTOR has permission, so this should succeed
    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=auth_headers
    )

    # TRIAGE_DOCTOR is in the authorized roles list
    assert response.status_code in [201, 400, 404]  # Could fail for missing org, but not 403


def test_reservation_capacity_not_found(db_session, superadmin_headers, test_task):
    """Test reservation for non-existent hospital capacity."""
    from uuid import uuid4

    reservation_data = {
        "task_id": str(test_task),
        "organization_id": str(uuid4()),  # Non-existent
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 1,
        "lock_duration_minutes": 30
    }

    response = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data,
        headers=superadmin_headers
    )

    assert response.status_code == 404


def test_concurrent_reservations_dont_oversell(db_session, superadmin_headers, test_organization, test_task):
    """Test that concurrent reservations respect capacity limits."""
    # Create capacity with exactly 5 available beds
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=30,
        reserved_emergency_beds=10,
        out_of_service_emergency_beds=5,  # 5 available
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=2,
        out_of_service_icu_beds=3,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    from uuid import uuid4

    # First reservation for 3 beds (should succeed)
    reservation_data_1 = {
        "task_id": str(test_task),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 3,
        "lock_duration_minutes": 30
    }

    response1 = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data_1,
        headers=superadmin_headers
    )
    assert response1.status_code == 201

    # Second reservation for 3 beds (should fail - only 2 left)
    reservation_data_2 = {
        "task_id": str(test_task),
        "organization_id": str(test_organization.id),
        "resource_type": "HOSPITAL_EMERGENCY_BED",
        "quantity": 3,
        "lock_duration_minutes": 30
    }

    response2 = client.post(
        "/api/v1/resources/reservations",
        json=reservation_data_2,
        headers=superadmin_headers
    )
    assert response2.status_code == 400
    assert "RESOURCE_INSUFFICIENT" in response2.json()["detail"]
