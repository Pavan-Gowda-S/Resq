"""
Test suite for resource and capacity management API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.models import HospitalCapacity, AmbulanceStatus, ResourceInventory


client = TestClient(app)


def test_search_hospitals_by_location(db_session, auth_headers, test_organization):
    """Test spatial search for hospitals within radius."""
    # Create hospital capacity for test organization
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

    # Search near Ernakulam (test org location is 76.2711, 10.8505)
    response = client.get(
        "/api/v1/resources/hospitals/search?lat=10.85&lng=76.27&radius_km=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "results" in data
    assert data["count"] >= 1

    # Verify result structure
    if data["count"] > 0:
        hospital = data["results"][0]
        assert "organization_id" in hospital
        assert "hospital_name" in hospital
        assert "distance_km" in hospital
        assert "available_emergency_beds" in hospital
        assert "available_icu_beds" in hospital
        assert "has_trauma_center" in hospital


def test_search_hospitals_with_availability_filter(db_session, auth_headers, test_organization):
    """Test hospital search with minimum availability filters."""
    # Create capacity with specific availability
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=30,
        reserved_emergency_beds=0,
        out_of_service_emergency_beds=0,
        total_icu_beds=20,
        occupied_icu_beds=15,
        reserved_icu_beds=0,
        out_of_service_icu_beds=0,
        has_trauma_center=True,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    # Search with filter requiring 10+ emergency beds
    response = client.get(
        "/api/v1/resources/hospitals/search?lat=10.85&lng=76.27&radius_km=50&min_emergency_available=10",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # All results should have at least 10 available emergency beds
    for hospital in data["results"]:
        assert hospital["available_emergency_beds"] >= 10


def test_get_hospital_capacity(db_session, auth_headers, test_organization):
    """Test getting hospital capacity details."""
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

    response = client.get(
        f"/api/v1/resources/hospitals/{test_organization.id}/capacity",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert data["organization_id"] == str(test_organization.id)
    assert data["total_emergency_beds"] == 50
    assert data["occupied_emergency_beds"] == 20
    assert data["reserved_emergency_beds"] == 5
    assert data["out_of_service_emergency_beds"] == 5
    assert data["available_emergency_beds"] == 20  # 50 - 20 - 5 - 5
    assert data["total_icu_beds"] == 20
    assert data["available_icu_beds"] == 5  # 20 - 10 - 2 - 3


def test_update_hospital_capacity_by_org_admin(db_session, test_organization, test_org_admin, org_admin_headers):
    """Test updating hospital capacity by organization admin."""
    # Create initial capacity
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=0,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=0,
        out_of_service_icu_beds=3,
        has_trauma_center=False,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    # Update capacity
    update_data = {
        "occupied_emergency_beds": 25,
        "total_icu_beds": 25,
        "has_trauma_center": True
    }

    response = client.put(
        f"/api/v1/resources/hospitals/{test_organization.id}/capacity",
        json=update_data,
        headers=org_admin_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert data["occupied_emergency_beds"] == 25
    assert data["total_icu_beds"] == 25
    assert data["has_trauma_center"] is True


def test_update_hospital_capacity_unauthorized(db_session, auth_headers, test_organization):
    """Test that non-admin users cannot update capacity."""
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=20,
        reserved_emergency_beds=0,
        out_of_service_emergency_beds=5,
        total_icu_beds=20,
        occupied_icu_beds=10,
        reserved_icu_beds=0,
        out_of_service_icu_beds=3,
        has_trauma_center=False,
        
        
    )
    db_session.add(capacity)
    db_session.commit()

    # Try to update as regular user (TRIAGE_DOCTOR)
    update_data = {"occupied_emergency_beds": 25}

    response = client.put(
        f"/api/v1/resources/hospitals/{test_organization.id}/capacity",
        json=update_data,
        headers=auth_headers
    )

    assert response.status_code == 403


def test_search_inventory(db_session, auth_headers, test_organization):
    """Test searching resource inventory."""
    # Create inventory items
    inventory1 = ResourceInventory(
        organization_id=test_organization.id,
        category="MEDICAL_SUPPLY",
        item_code="BLOOD-O-POS",
        item_name="O+ Blood Units",
        unit="UNITS",
        total_quantity=50,
        reserved_quantity=5
    )
    inventory2 = ResourceInventory(
        organization_id=test_organization.id,
        category="EQUIPMENT",
        item_code="BOAT-INFLT-6P",
        item_name="Inflatable Rescue Boat",
        unit="PIECES",
        total_quantity=10,
        reserved_quantity=2
    )
    db_session.add(inventory1)
    db_session.add(inventory2)
    db_session.commit()

    # Search all inventory
    response = client.get(
        "/api/v1/resources/inventory/search",
        headers=auth_headers
    )

    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2


def test_search_inventory_by_category(db_session, auth_headers, test_organization):
    """Test filtering inventory by category."""
    inventory = ResourceInventory(
        organization_id=test_organization.id,
        category="MEDICAL_SUPPLY",
        item_code="OXY-CYL-10L",
        item_name="Oxygen Cylinder 10L",
        unit="PIECES",
        total_quantity=100,
        reserved_quantity=10
    )
    db_session.add(inventory)
    db_session.commit()

    response = client.get(
        "/api/v1/resources/inventory/search?category=MEDICAL_SUPPLY",
        headers=auth_headers
    )

    assert response.status_code == 200
    items = response.json()

    for item in items:
        assert item["category"] == "MEDICAL_SUPPLY"


def test_create_inventory_item(db_session, superadmin_headers, test_organization):
    """Test creating inventory item."""
    inventory_data = {
        "organization_id": str(test_organization.id),
        "category": "RELIEF_MATERIAL",
        "item_code": "FOOD-DRY-RAT",
        "item_name": "Dry Food Ration Pack",
        "unit": "KG",
        "total_quantity": 500,
        "reserved_quantity": 50
    }

    response = client.post(
        "/api/v1/resources/inventory",
        json=inventory_data,
        headers=superadmin_headers
    )

    assert response.status_code == 201
    data = response.json()

    assert data["category"] == "RELIEF_MATERIAL"
    assert data["item_code"] == "FOOD-DRY-RAT"
    assert data["total_quantity"] == 500
    assert data["reserved_quantity"] == 50
    assert data["available_quantity"] == 450


def test_search_hospitals_unauthenticated(db_session):
    """Test that hospital search requires authentication."""
    response = client.get(
        "/api/v1/resources/hospitals/search?lat=10.85&lng=76.27&radius_km=50"
    )
    assert response.status_code == 401


def test_hospital_capacity_not_found(db_session, auth_headers):
    """Test getting capacity for non-existent hospital."""
    from uuid import uuid4
    fake_id = uuid4()

    response = client.get(
        f"/api/v1/resources/hospitals/{fake_id}/capacity",
        headers=auth_headers
    )
    assert response.status_code == 404
