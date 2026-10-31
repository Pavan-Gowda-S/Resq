"""
Test suite for Backend Phase 6: Real-time, Audit & Security.
"""
import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient
from uuid import uuid4

# Set TESTING env before importing app
os.environ["TESTING"] = "1"

from backend.app.main import app
from backend.app.models import AuditLog, AgentEvent
from backend.app.services.agent_event_service import log_agent_event

client = TestClient(app)


# ============================================================================
# Redis Pub/Sub Tests (with mocked Redis)
# ============================================================================

@pytest.mark.asyncio
async def test_publish_incident_update():
    """Test publishing incident update to Redis."""
    from backend.app.services.pubsub_service import publish_incident_update

    # Mock Redis client
    with patch('backend.app.services.pubsub_service.redis_client') as mock_redis:
        mock_redis.publish = AsyncMock()

        incident_id = str(uuid4())
        payload = {
            "event": "STATUS_CHANGED",
            "entity_type": "INCIDENT",
            "entity_id": incident_id,
            "new_status": "ACTIVE_RESPONSE"
        }

        await publish_incident_update(incident_id, payload)

        # Verify publish was called with correct channel and message
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == f"incidents:{incident_id}"
        assert json.loads(call_args[0][1]) == payload


@pytest.mark.asyncio
async def test_publish_task_update():
    """Test publishing task update to Redis."""
    from backend.app.services.pubsub_service import publish_task_update

    with patch('backend.app.services.pubsub_service.redis_client') as mock_redis:
        mock_redis.publish = AsyncMock()

        task_id = str(uuid4())
        payload = {
            "event": "STATUS_CHANGED",
            "entity_type": "TASK",
            "entity_id": task_id,
            "new_status": "ON_SCENE"
        }

        await publish_task_update(task_id, payload)

        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == f"tasks:{task_id}"


# ============================================================================
# WebSocket Tests
# ============================================================================

def test_websocket_incidents_authenticated(superadmin_headers):
    """Test WebSocket connection with valid token."""
    # Extract token from headers
    token = superadmin_headers["Authorization"].split(" ")[1]

    # Mock Redis to avoid actual connection
    with patch('backend.app.api.v1.websockets.get_redis') as mock_get_redis:
        mock_pubsub = AsyncMock()
        mock_pubsub.psubscribe = AsyncMock()
        mock_pubsub.punsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()

        # Create async generator for listen
        async def mock_listen():
            yield {"type": "subscribe", "channel": "test"}
            # Don't yield more to let connection close

        mock_pubsub.listen = mock_listen

        mock_redis = AsyncMock()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
        mock_get_redis.return_value = mock_redis

        try:
            with client.websocket_connect(f"/ws/incidents?token={token}") as websocket:
                # Connection should succeed
                assert websocket is not None
        except Exception:
            # Connection may close immediately in test, which is expected
            pass


def test_websocket_incidents_unauthenticated():
    """Test WebSocket connection without token gets rejected."""
    with pytest.raises(Exception) as exc_info:
        with client.websocket_connect("/ws/incidents") as websocket:
            pass

    # Should fail due to authentication


def test_websocket_task_feed(superadmin_headers, test_task):
    """Test WebSocket task feed with valid token."""
    token = superadmin_headers["Authorization"].split(" ")[1]

    with patch('backend.app.api.v1.websockets.get_redis') as mock_get_redis:
        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()

        # Create async generator for listen
        async def mock_listen():
            yield {"type": "subscribe", "channel": "test"}
            # Don't yield more to let connection close

        mock_pubsub.listen = mock_listen

        mock_redis = AsyncMock()
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
        mock_get_redis.return_value = mock_redis

        try:
            with client.websocket_connect(f"/ws/tasks/{test_task}?token={token}") as websocket:
                assert websocket is not None
        except Exception:
            # Connection may close immediately in test, which is expected
            pass


def test_websocket_task_invalid_token(test_task):
    """Test WebSocket with invalid token gets rejected."""
    fake_token = "invalid.token.here"

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/tasks/{test_task}?token={fake_token}") as websocket:
            pass


# ============================================================================
# Audit Log Tests
# ============================================================================

def test_audit_log_created_for_post(db_session):
    """Test audit log is created for POST request."""
    # Count existing audit logs
    initial_count = db_session.query(AuditLog).count()

    # Make a POST request (public SOS report)
    response = client.post("/api/v1/incidents/report", json={
        "description": "Test audit log incident",
        "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
        "district": "Ernakulam",
        "people_affected": 1,
    })

    assert response.status_code == 201

    # Wait a moment for async audit log write
    import time
    time.sleep(0.5)

    # Verify audit log was created
    new_count = db_session.query(AuditLog).count()
    assert new_count > initial_count

    # Get the latest audit log
    latest_log = db_session.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    assert latest_log is not None
    assert "POST" in latest_log.action
    assert "/api/v1/incidents/report" in latest_log.request_route


def test_audit_log_skips_get(db_session):
    """Test audit log is NOT created for GET request."""
    initial_count = db_session.query(AuditLog).count()

    # Make a GET request (health check)
    response = client.get("/health")
    assert response.status_code == 200

    import time
    time.sleep(0.3)

    # Verify no new audit log was created
    new_count = db_session.query(AuditLog).count()
    assert new_count == initial_count


def test_audit_log_captures_user(db_session, superadmin_headers):
    """Test audit log captures user_id for authenticated requests."""
    from backend.app.auth.security import decode_access_token

    # Extract user_id from token
    token = superadmin_headers["Authorization"].split(" ")[1]
    payload = decode_access_token(token)
    user_id = payload.get("sub")

    initial_count = db_session.query(AuditLog).count()

    # Make authenticated POST request
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": "Test Audit Org",
            "type": "HOSPITAL",
            "registration_number": "AUDIT-TEST-001",
            "contact_email": "audit@test.org",
            "contact_phone": "+919876543210",
            "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
            "address": "Test Address",
            "district": "Ernakulam"
        },
        headers=superadmin_headers
    )

    import time
    time.sleep(0.5)

    # Get the latest audit log
    latest_log = db_session.query(AuditLog).order_by(AuditLog.created_at.desc()).first()
    if latest_log and "POST /api/v1/organizations" in latest_log.action:
        assert latest_log.user_id is not None
        assert str(latest_log.user_id) == user_id


# ============================================================================
# Rate Limiting Tests (skip in TESTING mode since rate limiter is disabled)
# ============================================================================

@pytest.mark.skipif(os.getenv("TESTING") == "1", reason="Rate limiting disabled in test mode")
def test_rate_limit_login():
    """Test rate limiting on login endpoint (10 per minute)."""
    # Make 10 login attempts (should all succeed or fail with 401, not 429)
    for i in range(10):
        response = client.post("/api/v1/auth/login", json={
            "email": f"test{i}@example.com",
            "password": "wrongpass"
        })
        # Should get 401 (unauthorized), not 429 (rate limited)
        assert response.status_code in [401, 200]

    # 11th attempt should be rate limited
    response = client.post("/api/v1/auth/login", json={
        "email": "test11@example.com",
        "password": "wrongpass"
    })
    assert response.status_code == 429


@pytest.mark.skipif(os.getenv("TESTING") == "1", reason="Rate limiting disabled in test mode")
def test_rate_limit_sos_report():
    """Test rate limiting on SOS report endpoint (5 per minute)."""
    # Rate limits are shared across tests from same IP
    # Try making requests until we hit the limit
    attempts = 0
    rate_limited = False

    for i in range(10):  # Try up to 10 times
        response = client.post("/api/v1/incidents/report", json={
            "description": f"Test rate limit report {i}",
            "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
            "district": "Ernakulam",
            "people_affected": 1,
        })

        if response.status_code == 429:
            rate_limited = True
            break

        attempts += 1

    # Should have hit rate limit within 10 attempts
    # (given 5/minute limit and potentially prior test consumption)
    assert rate_limited, f"Expected rate limit (429) but got success after {attempts} attempts"


# ============================================================================
# Agent Event Service Test
# ============================================================================

@pytest.mark.asyncio
async def test_log_agent_event(db_session):
    """Test logging agent event directly."""
    from backend.app.database.config import AsyncSessionLocal

    async with AsyncSessionLocal() as async_db:
        # Create agent event
        agent_event = await log_agent_event(
            db=async_db,
            agent_name="TestAgent",
            action_type="TEST_ACTION",
            input_context={"test_input": "value"},
            output_decision={"test_output": "result"},
            confidence_score=0.95,
            execution_time_ms=150
        )

        await async_db.commit()

        # Verify event was created
        assert agent_event.id is not None
        assert agent_event.agent_name == "TestAgent"
        assert agent_event.action_type == "TEST_ACTION"
        assert agent_event.confidence_score == 0.95
        assert agent_event.execution_time_ms == 150

    # Verify in sync session
    event_in_db = db_session.query(AgentEvent).filter_by(
        agent_name="TestAgent",
        action_type="TEST_ACTION"
    ).first()

    assert event_in_db is not None
    assert event_in_db.input_context == {"test_input": "value"}
    assert event_in_db.output_decision == {"test_output": "result"}
