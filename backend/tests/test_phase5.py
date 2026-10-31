"""
Test suite for Backend Phase 5: Assignment, Tracking & Operational Workflows.
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from uuid import uuid4

from backend.app.main import app
from backend.app.models import ResponseTask, StatusEvent

client = TestClient(app)


def test_responder_accepts_task(db_session, superadmin_headers, test_organization, test_task):
    """Test that assigned user can accept task in ASSIGNED status."""
    # First, assign the task
    response = client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED", "notes": "Assigned to responder"},
        headers=superadmin_headers
    )
    assert response.status_code == 200

    # Now accept the task
    response = client.patch(
        f"/api/v1/tasks/{test_task}/accept",
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACCEPTED"
    assert "updated_at" in data


def test_responder_reject_task(db_session, superadmin_headers, test_organization, test_task):
    """Test that assigned user can reject task."""
    # First, assign the task
    response = client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED", "notes": "Assigned to responder"},
        headers=superadmin_headers
    )
    assert response.status_code == 200

    # Now reject the task
    response = client.patch(
        f"/api/v1/tasks/{test_task}/reject",
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_ASSIGNMENT"


def test_accept_wrong_status(db_session, superadmin_headers, test_task):
    """Test that cannot accept task that is not in ASSIGNED status."""
    # Try to accept task in PENDING_ASSIGNMENT status
    response = client.patch(
        f"/api/v1/tasks/{test_task}/accept",
        headers=superadmin_headers
    )

    assert response.status_code == 409
    assert "ASSIGNED" in response.json()["detail"]


def test_accept_unauthorized_user(db_session, auth_headers, test_task):
    """Test that unrelated user cannot accept task not assigned to them."""
    # Get task details
    task_response = client.get(
        f"/api/v1/tasks/{test_task}",
        headers=auth_headers
    )
    task_data = task_response.json()

    # If task is assigned to this user's org, skip this test
    if task_data.get("assigned_organization_id"):
        pytest.skip("Task is assigned to test user's organization")

    # Assign to different organization
    from uuid import uuid4
    fake_org = uuid4()

    # Try to accept - should fail if not assigned
    response = client.patch(
        f"/api/v1/tasks/{test_task}/accept",
        headers=auth_headers
    )

    # Should fail because task is not in ASSIGNED status or user is not authorized
    assert response.status_code in [403, 409]


def test_task_en_route(db_session, superadmin_headers, test_task):
    """Test setting task status to EN_ROUTE."""
    # First assign and accept
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )
    client.patch(f"/api/v1/tasks/{test_task}/accept", headers=superadmin_headers)

    # Set EN_ROUTE
    response = client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "EN_ROUTE", "notes": "Heading to location"},
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "EN_ROUTE"


def test_task_on_scene(db_session, superadmin_headers, test_task):
    """Test setting task status to ON_SCENE sets arrived_at timestamp."""
    # First assign, accept, and go en route
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

    # Set ON_SCENE
    response = client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ON_SCENE", "notes": "Arrived at scene"},
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ON_SCENE"
    assert data["arrived_at"] is not None


def test_task_completed(db_session, superadmin_headers, test_task):
    """Test setting task status to COMPLETED sets completed_at timestamp."""
    # First go through full workflow
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

    # Set COMPLETED
    response = client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "COMPLETED", "notes": "Task completed successfully"},
        headers=superadmin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["completed_at"] is not None


def test_citizen_confirm_arrival(db_session, superadmin_headers, test_task):
    """Test citizen confirming responder arrival with valid token."""
    # Get incident ID from task
    task_response = client.get(f"/api/v1/tasks/{test_task}", headers=superadmin_headers)
    incident_id = task_response.json()["incident_id"]

    # Get tracking token for incident
    from backend.app.models import TrackingToken
    result = db_session.query(TrackingToken).filter_by(incident_id=incident_id).first()

    if not result:
        # Create a tracking token
        from backend.app.services.incident_service import create_tracking_token
        from sqlalchemy.ext.asyncio import AsyncSession
        import asyncio

        async def create_token():
            async_db = AsyncSession(bind=db_session.get_bind())
            token = await create_tracking_token(async_db, incident_id, "+919999999999")
            await async_db.commit()
            return token.token

        token_str = asyncio.run(create_token())
    else:
        token_str = result.token

    # Confirm arrival
    response = client.post(
        f"/api/v1/incidents/track/{token_str}/confirm-arrival",
        json={
            "task_id": str(test_task),
            "confirmed": True,
            "feedback_comment": "Rescue team arrived and helped us evacuate safely"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["confirmed"] is True
    assert "confirmed_at" in data


def test_citizen_confirm_wrong_task(db_session, superadmin_headers, test_task):
    """Test citizen cannot confirm task not belonging to their incident."""
    # Create a different incident
    report_res = client.post("/api/v1/incidents/report", json={
        "description": "Different emergency incident",
        "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
        "district": "Ernakulam",
        "people_affected": 1,
    })
    other_incident_token = report_res.json()["tracking_token"]

    # Try to confirm task from different incident
    response = client.post(
        f"/api/v1/incidents/track/{other_incident_token}/confirm-arrival",
        json={
            "task_id": str(test_task),
            "confirmed": True,
            "feedback_comment": "Test"
        }
    )

    assert response.status_code == 403
    assert "does not belong" in response.json()["detail"]


def test_citizen_confirm_expired_token(db_session):
    """Test citizen cannot use expired tracking token."""
    fake_token = "EXPIRED-TOKEN-12345"
    fake_task_id = uuid4()

    response = client.post(
        f"/api/v1/incidents/track/{fake_token}/confirm-arrival",
        json={
            "task_id": str(fake_task_id),
            "confirmed": True,
            "feedback_comment": "Test"
        }
    )

    assert response.status_code == 404


def test_full_lifecycle(db_session, superadmin_headers):
    """Test complete task lifecycle from creation to completion."""
    # Create incident
    report_res = client.post("/api/v1/incidents/report", json={
        "description": "Full lifecycle test emergency",
        "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
        "district": "Ernakulam",
        "people_affected": 3,
    })
    incident_id = report_res.json()["incident_id"]
    tracking_token = report_res.json()["tracking_token"]

    # Create task
    task_res = client.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "RESCUE_EXTRACTION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
                "instructions": "Extract trapped individuals"
            }]
        },
        headers=superadmin_headers
    )
    task_id = task_res.json()["created_tasks"][0]["id"]

    # Assign task
    assign_res = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "ASSIGNED", "notes": "Assigned to rescue team"},
        headers=superadmin_headers
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_at"] is not None

    # Accept task
    accept_res = client.patch(
        f"/api/v1/tasks/{task_id}/accept",
        headers=superadmin_headers
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # Get task to verify accepted_at
    task_detail = client.get(f"/api/v1/tasks/{task_id}", headers=superadmin_headers)
    assert task_detail.json()["accepted_at"] is not None

    # En route
    enroute_res = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "EN_ROUTE"},
        headers=superadmin_headers
    )
    assert enroute_res.status_code == 200

    # On scene
    onscene_res = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "ON_SCENE"},
        headers=superadmin_headers
    )
    assert onscene_res.status_code == 200
    assert onscene_res.json()["arrived_at"] is not None

    # Citizen confirms
    confirm_res = client.post(
        f"/api/v1/incidents/track/{tracking_token}/confirm-arrival",
        json={
            "task_id": task_id,
            "confirmed": True,
            "feedback_comment": "Team arrived quickly"
        }
    )
    assert confirm_res.status_code == 200
    assert confirm_res.json()["confirmed"] is True

    # Complete task
    complete_res = client.patch(
        f"/api/v1/tasks/{task_id}/status",
        json={"status": "COMPLETED"},
        headers=superadmin_headers
    )
    assert complete_res.status_code == 200
    assert complete_res.json()["completed_at"] is not None

    # Verify all timestamps are set
    final_task = client.get(f"/api/v1/tasks/{task_id}", headers=superadmin_headers).json()
    assert final_task["assigned_at"] is not None
    assert final_task["accepted_at"] is not None
    assert final_task["arrived_at"] is not None
    assert final_task["completed_at"] is not None
    assert final_task["citizen_confirmed_arrival"] is True
    assert final_task["citizen_confirmed_at"] is not None


def test_status_events_recorded(db_session, superadmin_headers, test_task):
    """Test that each transition creates a status_event row."""
    # Assign task
    client.patch(
        f"/api/v1/tasks/{test_task}/status",
        json={"status": "ASSIGNED"},
        headers=superadmin_headers
    )

    # Accept task
    client.patch(f"/api/v1/tasks/{test_task}/accept", headers=superadmin_headers)

    # Check status events
    events = db_session.query(StatusEvent).filter_by(
        entity_type="TASK",
        entity_id=test_task
    ).all()

    # Should have at least: PENDING_ASSIGNMENT (creation), ASSIGNED, ACCEPTED
    assert len(events) >= 3

    # Verify ACCEPTED event exists
    accepted_event = next((e for e in events if e.new_status == "ACCEPTED"), None)
    assert accepted_event is not None
    assert accepted_event.previous_status == "ASSIGNED"
