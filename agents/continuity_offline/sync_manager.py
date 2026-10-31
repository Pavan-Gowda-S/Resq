"""
Continuity & Offline Agent - Sync Manager.
Manages offline event buffering, idempotency deduplication, and conflict detection.
"""
from typing import List, Dict, Any, Set
from agents.core.client import ResqApiClient
from agents.continuity_offline.schemas import OfflineEvent, SyncReplayResult


class OfflineSyncManager:
    """
    Manages offline event buffering and synchronization.

    Critical Safety Principles:
    1. UUID-based idempotency - duplicate event IDs rejected
    2. Non-authoritative timestamp - newest client timestamp NOT automatically authoritative
    3. Stale mutation rejection - offline events cannot overwrite server capacity
    """

    def __init__(self):
        self.queued_events: List[OfflineEvent] = []
        self.synced_event_ids: Set[str] = set()
        self.is_connected: bool = True

    def buffer_event(self, event: OfflineEvent) -> None:
        """
        Buffer event in offline queue when connection unavailable.

        Args:
            event: Offline event to buffer
        """
        if event.event_id not in self.synced_event_ids:
            self.queued_events.append(event)

    def simulate_offline(self) -> None:
        """Simulate network disconnection."""
        self.is_connected = False

    def simulate_online(self) -> None:
        """Simulate network reconnection."""
        self.is_connected = True

    async def synchronize_queued_events(
        self,
        device_id: str,
        client: ResqApiClient
    ) -> SyncReplayResult:
        """
        Synchronize queued offline events with backend.

        Performs:
        1. Dispatches queued events to backend via client.sync_events()
        2. Deduplicates previously seen event_ids (idempotency)
        3. Validates state machine legality (reject stale mutations)

        Args:
            device_id: Device identifier
            client: RESQ API client

        Returns:
            SyncReplayResult with sync statistics and conflicts
        """
        if not self.queued_events:
            return SyncReplayResult(
                device_id=device_id,
                total_events=0,
                synced_count=0,
                rejected_count=0,
                conflicts=[],
                replay_status="NO_EVENTS"
            )

        # Deduplicate events (idempotency check)
        unique_events = []
        rejected_duplicates = 0

        for event in self.queued_events:
            if event.event_id in self.synced_event_ids:
                rejected_duplicates += 1
            else:
                unique_events.append(event)

        if not unique_events:
            return SyncReplayResult(
                device_id=device_id,
                total_events=len(self.queued_events),
                synced_count=0,
                rejected_count=rejected_duplicates,
                conflicts=["All events were duplicates (idempotency rejection)"],
                replay_status="ALL_DUPLICATES"
            )

        # Convert to API format
        api_events = [
            {
                "event_id": event.event_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "action": event.action,
                "payload": event.payload,
                "client_timestamp": event.client_timestamp.isoformat(),
                "device_id": event.device_id
            }
            for event in unique_events
        ]

        try:
            # Synchronize with backend
            sync_response = await client.sync_events(device_id, api_events)

            synced_count = sync_response.get("synced_count", 0)
            rejected_count = sync_response.get("rejected_count", 0) + rejected_duplicates
            conflicts = sync_response.get("conflicts", [])

            # Mark successfully synced events
            for event in unique_events[:synced_count]:
                self.synced_event_ids.add(event.event_id)

            # Clear queued events that were processed
            self.queued_events = []

            # Determine replay status
            if synced_count == len(unique_events):
                replay_status = "SUCCESS"
            elif synced_count > 0:
                replay_status = "PARTIAL"
            else:
                replay_status = "FAILED"

            return SyncReplayResult(
                device_id=device_id,
                total_events=len(self.queued_events) + len(unique_events),
                synced_count=synced_count,
                rejected_count=rejected_count,
                conflicts=conflicts,
                replay_status=replay_status
            )

        except Exception as e:
            return SyncReplayResult(
                device_id=device_id,
                total_events=len(unique_events),
                synced_count=0,
                rejected_count=len(unique_events) + rejected_duplicates,
                conflicts=[f"Sync failed: {str(e)}"],
                replay_status="FAILED"
            )
