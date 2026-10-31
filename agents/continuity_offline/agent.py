"""
Continuity & Offline Agent - LangGraph Node.
Manages offline event synchronization and replay.
"""
from datetime import datetime
from typing import Optional
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.continuity_offline.sync_manager import OfflineSyncManager
from agents.continuity_offline.schemas import OfflineEvent


async def run_continuity_offline(
    state: AgentState,
    client: Optional[ResqApiClient] = None,
    sync_manager: Optional[OfflineSyncManager] = None
) -> AgentState:
    """
    Continuity & Offline Agent LangGraph node.

    Executes:
    1. Inspects offline_events in state
    2. Replays synchronized events via OfflineSyncManager
    3. Records sync results in audit_trail

    Critical Safety:
    - UUID-based idempotency prevents duplicate processing
    - Non-authoritative timestamp principle protects server capacity
    - Stale mutations rejected

    Args:
        state: Current LangGraph state dictionary
        client: Optional RESQ API client
        sync_manager: Optional sync manager (for testing)

    Returns:
        Updated state with sync results
    """

    # Initialize client if not provided
    if client is None:
        client = ResqApiClient()

    # Initialize sync manager if not provided
    if sync_manager is None:
        sync_manager = OfflineSyncManager()

    # Get offline events from state
    offline_events_data = state.get("offline_events", [])

    if not offline_events_data:
        # No offline events to sync
        return state

    # Convert to OfflineEvent objects
    offline_events = []
    for event_data in offline_events_data:
        try:
            event = OfflineEvent(
                event_id=event_data["event_id"],
                entity_type=event_data["entity_type"],
                entity_id=event_data["entity_id"],
                action=event_data["action"],
                payload=event_data["payload"],
                client_timestamp=datetime.fromisoformat(event_data["client_timestamp"].replace("Z", "+00:00")),
                device_id=event_data["device_id"]
            )
            offline_events.append(event)
        except Exception as e:
            # Skip malformed events
            continue

    if not offline_events:
        return state

    # Buffer events in sync manager
    for event in offline_events:
        sync_manager.buffer_event(event)

    # Get device ID (use first event's device_id)
    device_id = offline_events[0].device_id

    # Synchronize queued events
    sync_result = await sync_manager.synchronize_queued_events(device_id, client)

    # Store sync result in state
    state["sync_result"] = {
        "device_id": sync_result.device_id,
        "total_events": sync_result.total_events,
        "synced_count": sync_result.synced_count,
        "rejected_count": sync_result.rejected_count,
        "conflicts": sync_result.conflicts,
        "replay_status": sync_result.replay_status
    }

    # Append audit trail entry
    audit_entry = {
        "agent": "ContinuityOfflineAgent",
        "action": "offline_events_synchronized",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "results": {
            "device_id": sync_result.device_id,
            "total_events": sync_result.total_events,
            "synced_count": sync_result.synced_count,
            "rejected_count": sync_result.rejected_count,
            "replay_status": sync_result.replay_status
        }
    }

    if "audit_trail" not in state:
        state["audit_trail"] = []
    state["audit_trail"].append(audit_entry)

    # Update state metadata
    state["state_updated_at"] = datetime.utcnow()

    return state
