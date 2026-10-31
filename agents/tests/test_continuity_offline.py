"""
Tests for Continuity & Offline Agent.
Validates offline buffering, idempotency deduplication, state integration.
"""
import pytest
from datetime import datetime, UTC
from agents.continuity_offline.agent import run_continuity_offline
from agents.continuity_offline.sync_manager import OfflineSyncManager
from agents.continuity_offline.schemas import OfflineEvent, SyncReplayResult
from agents.core.state import AgentState
from agents.core.client import ResqApiClient


@pytest.fixture
def mock_client():
    """Mock ResqApiClient for testing."""
    class MockResqClient:
        async def sync_events(self, device_id: str, events: list):
            # Simulate successful sync
            return {
                "synced_count": len(events),
                "rejected_count": 0,
                "conflicts": []
            }

        async def close(self):
            pass

    return MockResqClient()


@pytest.fixture
def sample_offline_events():
    """Sample offline events for testing."""
    return [
        {
            "event_id": "evt-001",
            "entity_type": "reservation",
            "entity_id": "res-hospital-001",
            "action": "create",
            "payload": {"hospital_id": "hosp-001", "bed_type": "ICU"},
            "client_timestamp": "2026-10-31T08:00:00Z",
            "device_id": "device-field-001"
        },
        {
            "event_id": "evt-002",
            "entity_type": "task",
            "entity_id": "task-rescue-001",
            "action": "confirm",
            "payload": {"status": "COMPLETED"},
            "client_timestamp": "2026-10-31T08:05:00Z",
            "device_id": "device-field-001"
        }
    ]


@pytest.mark.asyncio
async def test_offline_event_buffering(mock_client):
    """Test offline event buffering in sync manager."""
    sync_manager = OfflineSyncManager()

    event = OfflineEvent(
        event_id="evt-001",
        entity_type="reservation",
        entity_id="res-001",
        action="create",
        payload={"hospital_id": "hosp-001"},
        client_timestamp=datetime.now(UTC),
        device_id="device-001"
    )

    sync_manager.buffer_event(event)

    assert len(sync_manager.queued_events) == 1
    assert sync_manager.queued_events[0].event_id == "evt-001"


@pytest.mark.asyncio
async def test_idempotency_deduplication(mock_client):
    """Test UUID-based idempotency deduplication."""
    sync_manager = OfflineSyncManager()

    event = OfflineEvent(
        event_id="evt-dedup-001",
        entity_type="reservation",
        entity_id="res-001",
        action="create",
        payload={"hospital_id": "hosp-001"},
        client_timestamp=datetime.now(UTC),
        device_id="device-001"
    )

    # Buffer event once and sync
    sync_manager.buffer_event(event)
    result = await sync_manager.synchronize_queued_events("device-001", mock_client)

    # First sync should process event
    assert result.synced_count == 1

    # Try to buffer the same event_id again (should be rejected as duplicate)
    sync_manager.buffer_event(event)
    result2 = await sync_manager.synchronize_queued_events("device-001", mock_client)

    # Should detect as duplicate since event_id already synced
    assert result2.replay_status in ["ALL_DUPLICATES", "NO_EVENTS"] or result2.rejected_count > 0


@pytest.mark.asyncio
async def test_offline_agent_state_integration(mock_client, sample_offline_events):
    """Test continuity offline agent integration with state."""
    state: AgentState = {
        "incident_id": "inc-village-c-offline",
        "offline_events": sample_offline_events,
        "audit_trail": []
    }

    sync_manager = OfflineSyncManager()

    updated_state = await run_continuity_offline(state, mock_client, sync_manager)

    # Verify sync result recorded
    assert "sync_result" in updated_state
    assert updated_state["sync_result"]["device_id"] == "device-field-001"
    assert updated_state["sync_result"]["total_events"] >= 0

    # Verify audit trail entry
    assert len(updated_state["audit_trail"]) > 0
    audit_entry = updated_state["audit_trail"][-1]
    assert audit_entry["agent"] == "ContinuityOfflineAgent"
    assert audit_entry["action"] == "offline_events_synchronized"


@pytest.mark.asyncio
async def test_empty_offline_events(mock_client):
    """Test handling of empty offline events list."""
    state: AgentState = {
        "incident_id": "inc-test",
        "offline_events": [],
        "audit_trail": []
    }

    sync_manager = OfflineSyncManager()

    updated_state = await run_continuity_offline(state, mock_client, sync_manager)

    # Should return state unchanged
    assert "sync_result" not in updated_state


@pytest.mark.asyncio
async def test_malformed_offline_events(mock_client):
    """Test handling of malformed offline events."""
    state: AgentState = {
        "incident_id": "inc-test",
        "offline_events": [
            {
                "event_id": "evt-001",
                # Missing required fields
                "entity_type": "reservation"
            }
        ],
        "audit_trail": []
    }

    sync_manager = OfflineSyncManager()

    # Should not crash, should skip malformed events
    updated_state = await run_continuity_offline(state, mock_client, sync_manager)

    # May or may not have sync_result depending on whether any valid events
    assert "incident_id" in updated_state


@pytest.mark.asyncio
async def test_sync_manager_offline_mode():
    """Test sync manager offline/online simulation."""
    sync_manager = OfflineSyncManager()

    assert sync_manager.is_connected is True

    sync_manager.simulate_offline()
    assert sync_manager.is_connected is False

    sync_manager.simulate_online()
    assert sync_manager.is_connected is True


@pytest.mark.asyncio
async def test_sync_replay_result_schema():
    """Test SyncReplayResult schema validation."""
    result = SyncReplayResult(
        device_id="device-001",
        total_events=5,
        synced_count=4,
        rejected_count=1,
        conflicts=["Stale reservation: capacity changed"],
        replay_status="PARTIAL"
    )

    assert result.device_id == "device-001"
    assert result.total_events == 5
    assert result.synced_count == 4
    assert result.rejected_count == 1
    assert len(result.conflicts) == 1
    assert result.replay_status == "PARTIAL"


@pytest.mark.asyncio
async def test_no_events_sync_result(mock_client):
    """Test sync result when no events queued."""
    sync_manager = OfflineSyncManager()

    result = await sync_manager.synchronize_queued_events("device-001", mock_client)

    assert result.total_events == 0
    assert result.synced_count == 0
    assert result.replay_status == "NO_EVENTS"
