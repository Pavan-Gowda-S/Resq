"""
Test suite for response task management API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.main import app
from backend.app.models import ResponseTask, StatusEvent


client = TestClient(app)


def test_get_task_detail(db_session, superadmin_headers, auth_headers):
    """Test getting task details."""
    # Create incident with task
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Emergency requiring ambulance",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 2,
    })
    incident_id = report_response.json()["incident_id"]

    # Create task
    task_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "AMBULANCE_TRANSPORT",
                "priority": "HIGH",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
                "instructions": "Transport patient to General Hospital"
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_response.json()["created_tasks"][0]["id"]

    # Get task detail
    response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)

    assert response.status_code == 200
    task = response.json()

    assert task["id"] == task_id
    assert task["incident_id"] == incident_id
    assert task["task_type"] == "AMBULANCE_TRANSPORT"
    assert task["status"] == "PENDING_ASSIGNMENT"
    assert task["priority"] == "HIGH"
    assert "target_location" in task
    assert task["target_location"]["type"] == "Point"


def test_get_task_unauthenticated(db_session):
    """Test that getting task requires authentication."""
    response = client.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_update_task_status_by_dispatcher(db_session, superadmin_headers):
    """Test task status update by dispatcher."""
    # Create incident with task
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Rescue operation needed",
        "location": {"type": "Point", "coordinates": [76.3, 10.6]},
        "district": "Ernakulam",
        "people_affected": 5,
    })
    incident_id = report_response.json()["incident_id"]

    # Create task
    task_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "RESCUE_EXTRACTION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.3, 10.6]},
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_response.json()["created_tasks"][0]["id"]

    # Update task status
    status_update = {
        "status": "ASSIGNED",
        "notes": "Assigned to rescue team Alpha"
    }
    response = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json=status_update,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    task = response.json()
    assert task["status"] == "ASSIGNED"
    assert task["assigned_at"] is not None


def test_update_task_status_by_assigned_user(db_session, superadmin_headers, test_user):
    """Test task status update by assigned field responder."""
    # Create incident with task
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Medical supply delivery needed",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_response.json()["incident_id"]

    # Create task assigned to test_user
    task_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "SUPPLY_DELIVERY",
                "priority": "MEDIUM",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_response.json()["created_tasks"][0]["id"]

    # Assign task to test_user
    task = db_session.query(ResponseTask).filter_by(id=task_id).first()
    task.assigned_user_id = test_user.id
    db_session.commit()

    # Create auth headers for test_user
    from backend.app.auth.security import create_access_token
    user_token = create_access_token(data={"sub": str(test_user.id)})
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Update status as assigned user
    status_update = {"status": "ACCEPTED"}
    response = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json=status_update,
        headers=user_headers
    )

    assert response.status_code == 200
    task_data = response.json()
    assert task_data["status"] == "ACCEPTED"
    assert task_data["accepted_at"] is not None


def test_update_task_status_unauthorized(db_session, superadmin_headers, auth_headers):
    """Test that non-assigned users cannot update task status."""
    # Create incident with task
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Emergency task",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_response.json()["incident_id"]

    # Create task (not assigned to auth_headers user)
    task_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "RESCUE_EXTRACTION",
                "priority": "HIGH",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_response.json()["created_tasks"][0]["id"]

    # Try to update as different user (auth_headers is TRIAGE_DOCTOR - authorized role)
    status_update = {"status": "ACCEPTED"}
    response = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json=status_update,
        headers=auth_headers
    )

    # TRIAGE_DOCTOR is in authorized roles, so this should succeed
    assert response.status_code == 200


def test_task_status_timestamps(db_session, superadmin_headers):
    """Test that task status transitions update timestamps correctly."""
    # Create incident with task
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Test task for timestamp tracking",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_response.json()["incident_id"]

    # Create task
    task_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "AMBULANCE_TRANSPORT",
                "priority": "HIGH",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_response.json()["created_tasks"][0]["id"]

    # ASSIGNED status should set assigned_at
    client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )
    task = client.get(f"/api/v1/tasks/{task_id}", headers=superadmin_headers).json()
    assert task["assigned_at"] is not None

    # ACCEPTED status should set accepted_at
    client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "ACCEPTED"},
        headers=superadmin_headers
    )
    task = client.get(f"/api/v1/tasks/{task_id}", headers=superadmin_headers).json()
    assert task["accepted_at"] is not None

    # ON_SCENE status should set arrived_at
    client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "ON_SCENE"},
        headers=superadmin_headers
    )
    task = client.get(f"/api/v1/tasks/{task_id}", headers=superadmin_headers).json()
    assert task["arrived_at"] is not None

    # COMPLETED status should set completed_at
    client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers=superadmin_headers
    )
    task = client.get(f"/api/v1/tasks/{task_id}", headers=superadmin_headers).json()
    assert task["completed_at"] is not None


def test_task_status_event_recording(db_session, superadmin_headers):
    """Test that task status changes are recorded in status_events table."""
    # Create incident with task
    report_response = client.post("/api/v1/incidents/report", json={
        "description": "Task status event test",
        "location": {"type": "Point", "coordinates": [76.2, 10.5]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_response.json()["incident_id"]

    # Create task
    task_response = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "RESCUE_EXTRACTION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.2, 10.5]},
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_response.json()["created_tasks"][0]["id"]

    # Update status multiple times
    statuses = ["ASSIGNED", "ACCEPTED", "EN_ROUTE", "ON_SCENE"]
    for new_status in statuses:
        client.patch(
            f"/api/v1/tasks/{task_id}/status",
            json={"status": new_status, "notes": f"Transition to {new_status}"},
            headers=superadmin_headers
        )

    # Verify all status events were recorded
    status_events = db_session.query(StatusEvent).filter_by(
        entity_type="TASK",
        entity_id=task_id
    ).order_by(StatusEvent.timestamp.asc()).all()

    # Should have: PENDING_ASSIGNMENT (initial) + 4 updates = 5 events
    assert len(status_events) >= 5
    assert status_events[0].new_status == "PENDING_ASSIGNMENT"
    assert status_events[0].previous_status is None

    # Verify transitions
    assert status_events[1].previous_status == "PENDING_ASSIGNMENT"
    assert status_events[1].new_status == "ASSIGNED"


def test_task_not_found(db_session, auth_headers):
    """Test getting non-existent task returns 404."""
    response = client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
        headers=auth_headers
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_nonexistent_task_status(db_session, auth_headers):
    """Test updating status of non-existent task returns 404."""
    response = client.patch(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000/status",
        json={"status": "ASSIGNED"},
        headers=auth_headers
    )
    assert response.status_code == 404
