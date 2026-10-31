"""
Test suite for Backend Phase 7: Offline Synchronization.
"""
import os
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.testclient import TestClient

# Set TESTING env before importing app
os.environ["TESTING"] = "1"

from backend.app.main import app
from backend.app.models import ResponseTask, Incident, AuditLog

client = TestClient(app)


def test_sync_single_task_status_update(db_session, superadmin_headers, test_task):
    """Test syncing single UPDATE_STATUS event for a TASK."""
    # First, set task to ASSIGNED status
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )

    # Create sync request
    event_id = uuid4()
    sync_request = {
        "device_id": "dev_boat_team_04",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(test_task),
            "action": "UPDATE_STATUS",
            "payload": {"status": "ACCEPTED"},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 1
    assert data["rejected_count"] == 0
    assert len(data["conflicts"]) == 0

    # Verify task status was updated
    task_response = client.get(f"/api/v1/tasks/{test_task}", headers=superadmin_headers)
    assert task_response.json()["status"] == "ACCEPTED"


def test_sync_multiple_events_in_order(db_session, superadmin_headers, test_task):
    """Test syncing multiple events in order on same task."""
    # Set task to ASSIGNED
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )

    # Create multiple events
    sync_request = {
        "device_id": "dev_boat_team_05",
        "events": [
            {
                "event_id": str(uuid4()),
                "entity_type": "TASK",
                "entity_id": str(test_task),
                "action": "UPDATE_STATUS",
                "payload": {"status": "ACCEPTED"},
                "client_timestamp": "2026-10-31T11:00:00Z"
            },
            {
                "event_id": str(uuid4()),
                "entity_type": "TASK",
                "entity_id": str(test_task),
                "action": "UPDATE_STATUS",
                "payload": {"status": "EN_ROUTE"},
                "client_timestamp": "2026-10-31T11:05:00Z"
            },
            {
                "event_id": str(uuid4()),
                "entity_type": "TASK",
                "entity_id": str(test_task),
                "action": "UPDATE_STATUS",
                "payload": {"status": "ON_SCENE"},
                "client_timestamp": "2026-10-31T11:15:00Z"
            }
        ]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 3
    assert data["rejected_count"] == 0

    # Verify final status
    task_response = client.get(f"/api/v1/tasks/{test_task}", headers=superadmin_headers)
    assert task_response.json()["status"] == "ON_SCENE"


def test_sync_idempotent_resubmission(db_session, superadmin_headers, test_task):
    """Test that resubmitting same event_id is idempotent."""
    # Set task to ASSIGNED
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )

    event_id = uuid4()
    sync_request = {
        "device_id": "dev_boat_team_06",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(test_task),
            "action": "UPDATE_STATUS",
            "payload": {"status": "ACCEPTED"},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    # First submission
    response1 = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )
    assert response1.status_code == 200
    assert response1.json()["synced_count"] == 1

    # Second submission (same event_id)
    response2 = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )
    assert response2.status_code == 200
    data = response2.json()
    assert data["synced_count"] == 1  # Still counts as synced
    assert data["rejected_count"] == 0
    assert len(data["conflicts"]) == 0

    # Verify task status unchanged (not applied twice)
    task_response = client.get(f"/api/v1/tasks/{test_task}", headers=superadmin_headers)
    assert task_response.json()["status"] == "ACCEPTED"


def test_sync_invalid_task_not_found(db_session, superadmin_headers):
    """Test sync with non-existent task ID."""
    fake_task_id = uuid4()
    event_id = uuid4()

    sync_request = {
        "device_id": "dev_boat_team_07",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(fake_task_id),
            "action": "UPDATE_STATUS",
            "payload": {"status": "ACCEPTED"},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 0
    assert data["rejected_count"] == 1
    assert len(data["conflicts"]) == 1
    assert "not found" in data["conflicts"][0]["reason"].lower()


def test_sync_invalid_status_transition(db_session, superadmin_headers, test_task):
    """Test sync with invalid status transition."""
    # Set task to COMPLETED
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )
    client.patch(f"/api/v1/tasks/{test_task}/accept", headers=superadmin_headers)
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "EN_ROUTE"},
        headers=superadmin_headers
    )
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ON_SCENE"},
        headers=superadmin_headers
    )
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "COMPLETED"},
        headers=superadmin_headers
    )

    # Try to change COMPLETED task to ASSIGNED
    event_id = uuid4()
    sync_request = {
        "device_id": "dev_boat_team_08",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(test_task),
            "action": "UPDATE_STATUS",
            "payload": {"status": "ASSIGNED"},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rejected_count"] == 1
    assert len(data["conflicts"]) == 1
    assert "invalid transition" in data["conflicts"][0]["reason"].lower()


def test_sync_unknown_action(db_session, superadmin_headers, test_task):
    """Test sync with unknown action type."""
    event_id = uuid4()
    sync_request = {
        "device_id": "dev_boat_team_09",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(test_task),
            "action": "DELETE_TASK",  # Unknown action
            "payload": {},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rejected_count"] == 1
    assert len(data["conflicts"]) == 1
    assert "unknown action" in data["conflicts"][0]["reason"].lower()


def test_sync_update_location(db_session, superadmin_headers, test_task):
    """Test UPDATE_LOCATION action."""
    event_id = uuid4()
    sync_request = {
        "device_id": "dev_boat_team_10",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(test_task),
            "action": "UPDATE_LOCATION",
            "payload": {
                "location": {
                    "type": "Point",
                    "coordinates": [76.3000, 10.8600]
                }
            },
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 1
    assert data["rejected_count"] == 0


def test_sync_incident_status_update(db_session, superadmin_headers):
    """Test UPDATE_STATUS on INCIDENT entity."""
    # Create an incident
    report_res = client.post("/api/v1/incidents/report", json={
        "description": "Test sync incident",
        "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    incident_id = report_res.json()["incident_id"]

    event_id = uuid4()
    sync_request = {
        "device_id": "dev_control_room_01",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "INCIDENT",
            "entity_id": incident_id,
            "action": "UPDATE_STATUS",
            "payload": {"status": "ACTIVE_RESPONSE"},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 1
    assert data["rejected_count"] == 0

    # Verify incident status
    incident_response = client.get(
        f"/api/v1/incidents/{incident_id}",
        headers=superadmin_headers
    )
    assert incident_response.json()["status"] == "ACTIVE_RESPONSE"


def test_sync_mixed_valid_invalid(db_session, superadmin_headers, test_task):
    """Test batch with both valid and invalid events."""
    # Set task to ASSIGNED
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )

    fake_task_id = uuid4()

    sync_request = {
        "device_id": "dev_boat_team_11",
        "events": [
            {
                "event_id": str(uuid4()),
                "entity_type": "TASK",
                "entity_id": str(test_task),
                "action": "UPDATE_STATUS",
                "payload": {"status": "ACCEPTED"},
                "client_timestamp": "2026-10-31T11:00:00Z"
            },
            {
                "event_id": str(uuid4()),
                "entity_type": "TASK",
                "entity_id": str(fake_task_id),  # Invalid task
                "action": "UPDATE_STATUS",
                "payload": {"status": "COMPLETED"},
                "client_timestamp": "2026-10-31T11:05:00Z"
            },
            {
                "event_id": str(uuid4()),
                "entity_type": "TASK",
                "entity_id": str(test_task),
                "action": "UPDATE_STATUS",
                "payload": {"status": "EN_ROUTE"},
                "client_timestamp": "2026-10-31T11:10:00Z"
            }
        ]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 2
    assert data["rejected_count"] == 1
    assert len(data["conflicts"]) == 1


def test_sync_requires_auth(db_session):
    """Test that sync endpoint requires authentication."""
    sync_request = {
        "device_id": "dev_boat_team_12",
        "events": [{
            "event_id": str(uuid4()),
            "entity_type": "TASK",
            "entity_id": str(uuid4()),
            "action": "UPDATE_STATUS",
            "payload": {"status": "ACCEPTED"},
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post("/api/v1/sync/events", json=sync_request)

    assert response.status_code == 401


def test_sync_confirm_arrival(db_session, superadmin_headers, test_task):
    """Test CONFIRM_ARRIVAL action."""
    event_id = uuid4()
    sync_request = {
        "device_id": "dev_boat_team_13",
        "events": [{
            "event_id": str(event_id),
            "entity_type": "TASK",
            "entity_id": str(test_task),
            "action": "CONFIRM_ARRIVAL",
            "payload": {
                "feedback_comment": "Rescue team arrived and evacuated safely"
            },
            "client_timestamp": "2026-10-31T11:45:20Z"
        }]
    }

    response = client.post(
        "/api/v1/sync/events",
        json=sync_request,
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["synced_count"] == 1
    assert data["rejected_count"] == 0

    # Verify citizen confirmation
    task_response = client.get(f"/api/v1/tasks/{test_task}", headers=superadmin_headers)
    task_data = task_response.json()
    assert task_data["citizen_confirmed_arrival"] is True
    assert task_data["citizen_confirmed_at"] is not None
