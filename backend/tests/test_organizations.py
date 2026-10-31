"""
Automated tests for organizations endpoints.
Tests organization CRUD operations and PostGIS location handling.
"""
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_create_organization_as_superadmin(superadmin_headers):
    """Test creating organization as superadmin."""
    response = client.post(
        "/api/v1/organizations",
        headers=superadmin_headers,
        json={
            "name": "Test Hospital",
            "type": "HOSPITAL",
            "registration_number": "TEST-HOSP-001",
            "verification_status": "VERIFIED",
            "contact_email": "test@hospital.org",
            "contact_phone": "+919876543210",
            "location": {
                "type": "Point",
                "coordinates": [76.2711, 10.8505]
            },
            "address": "123 Test Street, Test City",
            "district": "Ernakulam"
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert data["name"] == "Test Hospital"
    assert data["type"] == "HOSPITAL"
    assert data["district"] == "Ernakulam"

    # Verify PostGIS location format (GeoJSON)
    assert "location" in data
    assert data["location"]["type"] == "Point"
    assert data["location"]["coordinates"] == [76.2711, 10.8505]


def test_create_organization_without_permission(auth_headers):
    """Test creating organization without SUPERADMIN role returns 403."""
    response = client.post(
        "/api/v1/organizations",
        headers=auth_headers,
        json={
            "name": "Unauthorized Hospital",
            "type": "HOSPITAL",
            "registration_number": "UNAUTH-001",
            "verification_status": "PENDING",
            "contact_email": "unauth@hospital.org",
            "contact_phone": "+919876543211",
            "location": {
                "type": "Point",
                "coordinates": [76.2711, 10.8505]
            },
            "address": "Unauthorized Address",
            "district": "Ernakulam"
        }
    )

    assert response.status_code == 403


def test_create_organization_duplicate_registration(superadmin_headers, test_organization):
    """Test creating organization with duplicate registration number returns 400."""
    response = client.post(
        "/api/v1/organizations",
        headers=superadmin_headers,
        json={
            "name": "Duplicate Org",
            "type": "HOSPITAL",
            "registration_number": test_organization.registration_number,  # Duplicate
            "verification_status": "PENDING",
            "contact_email": "duplicate@org.com",
            "contact_phone": "+919876543212",
            "location": {
                "type": "Point",
                "coordinates": [76.2711, 10.8505]
            },
            "address": "Duplicate Address",
            "district": "Ernakulam"
        }
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_list_organizations(auth_headers, test_organization):
    """Test listing organizations."""
    response = client.get(
        "/api/v1/organizations",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    # Verify structure
    first_org = data[0]
    assert "id" in first_org
    assert "name" in first_org
    assert "type" in first_org
    assert "district" in first_org
    assert "location" in first_org


def test_list_organizations_filter_by_type(auth_headers, test_organization):
    """Test filtering organizations by type."""
    response = client.get(
        f"/api/v1/organizations?type={test_organization.type}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # All returned organizations should match the filter
    for org in data:
        assert org["type"] == test_organization.type


def test_list_organizations_filter_by_district(auth_headers, test_organization):
    """Test filtering organizations by district."""
    response = client.get(
        f"/api/v1/organizations?district={test_organization.district}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    # All returned organizations should match the filter
    for org in data:
        assert org["district"] == test_organization.district


def test_list_organizations_pagination(auth_headers):
    """Test organization list pagination."""
    response = client.get(
        "/api/v1/organizations?skip=0&limit=5",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 5


def test_get_organization_by_id(auth_headers, test_organization):
    """Test getting organization details by ID."""
    response = client.get(
        f"/api/v1/organizations/{test_organization.id}",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == str(test_organization.id)
    assert data["name"] == test_organization.name
    assert data["type"] == test_organization.type

    # Verify complete structure
    assert "registration_number" in data
    assert "verification_status" in data
    assert "contact_email" in data
    assert "contact_phone" in data
    assert "location" in data
    assert "address" in data
    assert "district" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_organization_not_found(auth_headers):
    """Test getting non-existent organization returns 404."""
    response = client.get(
        "/api/v1/organizations/00000000-0000-0000-0000-000000000000",
        headers=auth_headers
    )

    assert response.status_code == 404


def test_list_organizations_without_auth():
    """Test accessing organizations without authentication returns 401."""
    response = client.get("/api/v1/organizations")

    assert response.status_code == 401


def test_postgis_location_persistence(superadmin_headers):
    """Test that PostGIS coordinates are correctly persisted and retrieved."""
    # Create organization with specific coordinates
    test_coords = [75.7804, 11.2588]  # Kozhikode

    response = client.post(
        "/api/v1/organizations",
        headers=superadmin_headers,
        json={
            "name": "PostGIS Test Hospital",
            "type": "HOSPITAL",
            "registration_number": "POSTGIS-TEST-001",
            "verification_status": "VERIFIED",
            "contact_email": "postgis@test.org",
            "contact_phone": "+919876543299",
            "location": {
                "type": "Point",
                "coordinates": test_coords
            },
            "address": "PostGIS Test Address",
            "district": "Kozhikode"
        }
    )

    assert response.status_code == 201
    org_id = response.json()["id"]

    # Retrieve and verify coordinates match
    get_response = client.get(
        f"/api/v1/organizations/{org_id}",
        headers=superadmin_headers
    )

    assert get_response.status_code == 200
    retrieved_data = get_response.json()

    # Verify coordinates are correctly retrieved
    retrieved_coords = retrieved_data["location"]["coordinates"]
    assert retrieved_coords[0] == pytest.approx(test_coords[0], abs=0.0001)
    assert retrieved_coords[1] == pytest.approx(test_coords[1], abs=0.0001)
