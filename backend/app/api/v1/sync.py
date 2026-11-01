"""
Offline sync API router - handles field responder offline events and PES_HACK edge bridge integration.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from backend.app.database import get_db
from backend.app.auth.dependencies import get_current_user, require_role
from backend.app.schemas.sync import SyncRequest, SyncResponse
from backend.app.services.sync_service import process_sync_events
from backend.app.models.user import User
from backend.app.services.offline_bridge_sync import OfflineBridgeSyncService

router = APIRouter(prefix="/sync", tags=["Offline Sync"])
logger = logging.getLogger(__name__)


class OfflineSyncResponse(BaseModel):
    """Response model for offline sync operations."""
    status: str
    synced_count: int
    incidents: List[dict]


class WebhookSMSRecord(BaseModel):
    """Incoming SMS record from PES_HACK edge bridge webhook."""
    id: str
    emergency_type: str
    victim_status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_text: str
    sender: str
    confidence: float = 0.0
    timestamp: Optional[str] = None


class WebhookIngestResponse(BaseModel):
    """Response model for webhook ingestion."""
    status: str
    incident_id: Optional[str] = None
    incident_number: Optional[str] = None
    message: str


@router.post("/events", response_model=SyncResponse, status_code=status.HTTP_200_OK)
async def sync_events(
    request: SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Process batch of offline sync events.

    Field responders can submit events that were queued offline (no connectivity)
    and replay them server-side in order.

    - **Idempotent**: Same event_id can be submitted multiple times safely
    - **Ordered**: Events processed in submission order
    - **Partial success**: Some events may succeed while others are rejected
    """
    return await process_sync_events(request, current_user, db)


@router.post("/offline/pull", response_model=OfflineSyncResponse)
async def sync_offline_pull(
    limit: int = 50,
    since: Optional[str] = None,
    current_user: User = Depends(require_role("SUPERADMIN", "CONTROL_ROOM_DISPATCHER")),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch pull offline SMS records from PES_HACK edge bridge.

    Triggers autonomous agent dispatch for resource allocation.
    Requires SUPERADMIN or CONTROL_ROOM_DISPATCHER role.
    """
    sync_service = OfflineBridgeSyncService()

    # Fetch records from offline bridge
    records = await sync_service.fetch_offline_records(limit=limit, since=since)

    if not records:
        logger.info("No offline records found to sync")
        return OfflineSyncResponse(
            status="success",
            synced_count=0,
            incidents=[]
        )

    # Ingest each record
    ingested_incidents = []
    for record in records:
        try:
            incident = await sync_service.ingest_record(db, record)
            if incident:
                ingested_incidents.append({
                    "incident_id": str(incident.id),
                    "incident_number": incident.incident_number,
                    "status": incident.status,
                    "priority": incident.priority,
                    "hazard_type": incident.hazard_type,
                    "district": incident.district,
                })
        except Exception as e:
            logger.error(f"Failed to ingest record {record.get('id')}: {e}")
            continue

    logger.info(f"Synced {len(ingested_incidents)} incidents from offline bridge")

    return OfflineSyncResponse(
        status="success",
        synced_count=len(ingested_incidents),
        incidents=ingested_incidents
    )


@router.post("/offline/webhook", response_model=WebhookIngestResponse)
async def sync_offline_webhook(
    sms_record: WebhookSMSRecord,
    db: AsyncSession = Depends(get_db),
):
    """
    Real-time webhook endpoint for PES_HACK edge bridge SMS forwarding.

    Accepts single parsed SMS record and triggers immediate ingestion and agent dispatch.
    Public endpoint protected by API key validation (handled by PES_HACK bridge).
    """
    sync_service = OfflineBridgeSyncService()

    # Convert Pydantic model to dict for ingestion
    record_dict = sms_record.model_dump()

    try:
        incident = await sync_service.ingest_record(db, record_dict)

        if not incident:
            return WebhookIngestResponse(
                status="duplicate",
                incident_id=None,
                incident_number=None,
                message=f"SMS record {sms_record.id} already ingested"
            )

        logger.info(f"Webhook ingested SMS {sms_record.id} as incident {incident.incident_number}")

        return WebhookIngestResponse(
            status="ingested",
            incident_id=str(incident.id),
            incident_number=incident.incident_number,
            message=f"Successfully ingested and dispatched agents for SMS {sms_record.id}"
        )

    except Exception as e:
        logger.error(f"Webhook ingestion failed for SMS {sms_record.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest SMS record: {str(e)}"
        )
