"""
Offline sync API router.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.auth.dependencies import get_current_user
from backend.app.schemas.sync import SyncRequest, SyncResponse
from backend.app.services.sync_service import process_sync_events
from backend.app.models.user import User

router = APIRouter(prefix="/sync", tags=["Offline Sync"])


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
