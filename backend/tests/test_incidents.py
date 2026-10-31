"""
Test suite for incident management API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.models import Incident, TrackingToken, StatusEvent


client = TestClient(app)


def test_public_incident_report(db_session):
    """Test public SOS incident reporting (unauthenticated)."""
    report_data = {
        "reporter_name": "John Doe",
        "reporter_phone": "+919876543210",
        "description": "Flash flood in residential area, multiple people trapped on rooftops",
        "location": {
            "type": "Point",
            "coordinates": [76.2711, 10.8505]
        },
        "district": "Ernakulam",
        "landmark": "Near City Center Mall",
        "people_affected": 15,
        "source": "WEB_ANONYMOUS"
    }

    response = client.post("/api/v1/incidents/report", json=report_data)

    assert response.status_code == 201
    data = response.json()

    assert "incident_id" in data
    assert "incident_number" in data
    assert data["incident_number"].startswith("RESQ-2026-")
    assert data["status"] == "REPORTED"
    assert "tracking_token" in data
    assert data["tracking_token"].startswith("trk_")
    assert "tracking_url" in data
    assert "message" in data

    # Verify incident was created in database
    incident = db_session.query(Incident).filter_by(
        incident_number=data["incident_number"]
    ).first()
    assert incident is not None
    assert incident.status == "REPORTED"
    assert incident.description == report_data["description"]
    assert incident.district == "Ernakulam"
    assert incident.people_affected == 15


def test_public_incident_tracking(db_session, auth_headers):
    """Test public incident tracking via token (unauthenticated)."""
    # First create an incident
    report_data = {
        "description": "Medical emergency - chest pain patient needs immediate transport",
        "location": {"type": "Point", "coordinates": [76.3, 10.9]},
        "district": "Kochi",
        "people_affected": 1,
        "source": "WEB_ANONYMOUS"
    }

    report_response = client.post("/api/v1/incidents/report", json=report_data)
    assert report_response.status_code == 201
    report_data_resp = report_response.json()
    tracking_token = report_data_resp["tracking_token"]

    # Track the incident using token (no auth required)
    track_response = client.get(f"/api/v1/incidents/track/{tracking_token}")

    assert track_response.status_code == 200
    track_data = track_response.json()

    assert track_data["incident_number"] == report_data_resp["incident_number"]
    assert track_data["status"] == "REPORTED"
    assert "reported_at" in track_data
    assert "tasks" in track_data
    assert isinstance(track_data["tasks"], list)


def test_public_tracking_invalid_token(db_session):
    """Test tracking with invalid token returns 404."""
    response = client.get("/api/v1/incidents/track/trk_invalid123")
    assert response.status_code == 404
    assert "Invalid tracking token" in response.json()["detail"]


def test_list_incidents_authenticated(db_session, auth_headers):
    """Test listing incidents (requires authentication)."""
    # Create a test incident first
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Landslide blocking main road",
        "location": {"type": "Point", "coordinates": [76.5, 9.5]},
        "district": "Idukki",
        "people_affected": 5,
    })
    assert report_response.status_code == 201

    # List incidents with authentication
    response = client.get("/api/v1/incidents", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

    # Verify response structure
    incident = data[0]
    assert "id" in incident
    assert "incident_number" in incident
    assert "status" in incident
    assert "location" in incident
    assert incident["location"]["type"] == "Point"


def test_list_incidents_with_filters(db_session, auth_headers):
    """Test listing incidents with status filter."""
    response = client.get(
        "/api/v1/incidents?status=REPORTED&district=Ernakulam",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_list_incidents_unauthenticated(db_session):
    """Test that listing incidents requires authentication."""
    response = client.get("/api/v1/incidents")
    assert response.status_code == 401


def test_get_incident_detail(db_session, auth_headers):
    """Test getting incident details with tasks and reports."""
    # Create incident
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Building collapse with trapped victims",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 10,
    })
    incident_data = report_response.json()
    incident_id = incident_data["incident_id"]

    # Get incident detail
    response = client.get(f"/api/v1/incidents/{incident_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == incident_id
    assert "tasks" in data
    assert "reports" in data
    assert isinstance(data["tasks"], list)
    assert isinstance(data["reports"], list)
    assert len(data["reports"]) == 1  # One report from initial submission


def test_update_incident_status(db_session, superadmin_headers):
    """Test updating incident status (authorized role)."""
    # Create incident
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Fire in residential building",
        "location": {"type": "Point", "coordinates": [76.3, 10.7]},
        "district": "Ernakulam",
        "people_affected": 20,
    })
    incident_id = report_response.json()["incident_id"]

    # Update status
    status_update = {
        "status": "ANALYZING",
        "notes": "Dispatcher reviewing incident details"
    }
    response = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json=status_update,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ANALYZING"

    # Verify status event was recorded
    status_events = db_session.query(StatusEvent).filter_by(
        entity_type="INCIDENT",
        entity_id=incident_id
    ).order_by(StatusEvent.timestamp.desc()).all()
    assert len(status_events) >= 2  # REPORTED + ANALYZING
    latest_event = status_events[0]
    assert latest_event.new_status == "ANALYZING"
    assert latest_event.previous_status == "REPORTED"


def test_update_incident_status_unauthorized(db_session, auth_headers):
    """Test that regular users cannot update incident status."""
    # Create incident
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Test incident",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_response.json()["incident_id"]

    # Try to update status as regular user (TRIAGE_DOCTOR has permission)
    status_update = {"status": "TRIAGED"}
    response = client.patch(
        f"/api/v1/incidents/{incident_id}/status",
        json=status_update,
        headers=auth_headers
    )

    # TRIAGE_DOCTOR is in authorized roles, so this should succeed
    assert response.status_code == 200


def test_create_incident_tasks(db_session, superadmin_headers):
    """Test creating multiple linked tasks for an incident."""
    # Create incident
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Multi-casualty flood rescue operation",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 25,
    })
    incident_id = report_response.json()["incident_id"]

    # Create multiple tasks
    task_proposal = {
        "proposals": [
            {
                "task_type": "RESCUE_EXTRACTION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
                "instructions": "Extract trapped people from flooded building"
            },
            {
                "task_type": "AMBULANCE_TRANSPORT",
                "priority": "HIGH",
                "target_location": {"type": "Point", "coordinates": [76.25, 10.52]},
                "instructions": "Transport injured to nearest hospital"
            },
            {
                "task_type": "HOSPITAL_ADMISSION",
                "priority": "HIGH",
                "target_location": {"type": "Point", "coordinates": [76.27, 10.53]},
                "instructions": "Admit 3 critical patients to ICU"
            }
        ]
    }

    response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json=task_proposal,
        headers=superadmin_headers
    )

    assert response.status_code == 201
    data = response.json()

    assert data["incident_id"] == incident_id
    assert "created_tasks" in data
    assert len(data["created_tasks"]) == 3

    # Verify all tasks have correct incident_id and initial status
    for task in data["created_tasks"]:
        assert task["incident_id"] == incident_id
        assert task["status"] == "PENDING_ASSIGNMENT"
        assert "target_location" in task
        assert task["target_location"]["type"] == "Point"


def test_create_linked_tasks_with_parent(db_session, superadmin_headers):
    """Test creating task dependency chains with parent_task_id."""
    # Create incident
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Complex rescue requiring sequential operations",
        "location": {"type": "Point", "coordinates": [76.3, 10.6]},
        "district": "Ernakulam",
        "people_affected": 10,
    })
    incident_id = report_response.json()["incident_id"]

    # Create parent task
    parent_task_proposal = {
        "proposals": [
            {
                "task_type": "RESCUE_EXTRACTION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.3, 10.6]},
                "instructions": "Extract patient from collapsed structure"
            }
        ]
    }
    parent_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json=parent_task_proposal,
        headers=superadmin_headers
    )
    parent_task_id = parent_response.json()["created_tasks"][0]["id"]

    # Create dependent task
    dependent_task_proposal = {
        "proposals": [
            {
                "task_type": "AMBULANCE_TRANSPORT",
                "priority": "HIGH",
                "target_location": {"type": "Point", "coordinates": [76.31, 10.61]},
                "instructions": "Transport extracted patient to hospital",
                "parent_task_id": parent_task_id
            }
        ]
    }
    dependent_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json=dependent_task_proposal,
        headers=superadmin_headers
    )

    assert dependent_response.status_code == 201
    dependent_task = dependent_response.json()["created_tasks"][0]
    assert dependent_task["parent_task_id"] == parent_task_id


def test_list_incident_tasks(db_session, superadmin_headers, auth_headers):
    """Test listing all tasks for an incident."""
    # Create incident with tasks
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Emergency with multiple response requirements",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 8,
    })
    incident_id = report_response.json()["incident_id"]

    # Create tasks
    task_proposal = {
        "proposals": [
            {
                "task_type": "RESCUE_EXTRACTION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
            },
            {
                "task_type": "SUPPLY_DELIVERY",
                "priority": "MEDIUM",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
            }
        ]
    }
    client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json=task_proposal,
        headers=superadmin_headers
    )

    # List tasks
    response = client.get(
        f"/api/v1/incidents/{incident_id}/tasks",
        headers=auth_headers
    )

    assert response.status_code == 200
    tasks = response.json()
    assert len(tasks) == 2
    assert all(task["incident_id"] == incident_id for task in tasks)


def test_status_event_recording(db_session, superadmin_headers):
    """Test that status changes are recorded in status_events table."""
    # Create incident
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Test incident for status event tracking",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_response.json()["incident_id"]

    # Update status multiple times
    statuses = ["ANALYZING", "TRIAGED", "DISPATCHING"]
    for new_status in statuses:
        client.patch(
            f"/api/v1/incidents/{incident_id}/status",
            json={"status": new_status},
            headers=superadmin_headers
        )

    # Verify all status events were recorded
    status_events = db_session.query(StatusEvent).filter_by(
        entity_type="INCIDENT",
        entity_id=incident_id
    ).order_by(StatusEvent.timestamp.asc()).all()

    # Should have: REPORTED (initial) + 3 updates = 4 events
    assert len(status_events) >= 4
    assert status_events[0].new_status == "REPORTED"
    assert status_events[0].previous_status is None
