"""
Offline Bridge Sync Service - Ingests parsed SMS records from PES_HACK edge database
into central RESQ PostgreSQL, triggering autonomous resource allocation.
"""
import os
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.elements import WKTElement

from app.models.incident import Incident
from app.models.response_task import ResponseTask, TaskStatus
from app.models.tracking_token import TrackingToken
from app.services.incident_service import generate_unique_incident_number
from app.services.status_service import record_status_change
from app.services.task_dispatch_agent import dispatch_task
from app.services.hospital_routing_agent import route_to_hospital

logger = logging.getLogger(__name__)


class OfflineBridgeSyncService:
    """Service for syncing offline SMS records from PES_HACK edge bridge."""

    def __init__(
        self,
        bridge_base_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.bridge_base_url = bridge_base_url or os.getenv(
            "RESQ_OFFLINE_BRIDGE_URL",
            "http://127.0.0.1:8000"
        )
        self.api_key = api_key or os.getenv(
            "RESQ_MAS_API_KEY",
            "resq-mas-bridge-secret-2026"
        )

    async def fetch_offline_records(
        self,
        limit: int = 50,
        since: Optional[str] = None
    ) -> list[dict]:
        """
        Fetch parsed offline SMS records from the edge bridge.

        Args:
            limit: Maximum number of records to fetch
            since: ISO timestamp to fetch records after (optional)

        Returns:
            List of parsed SMS record dictionaries
        """
        url = f"{self.bridge_base_url}/api/query-offline"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "limit": limit,
            "db_status": "parsed",
        }
        if since:
            payload["since"] = since

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

                # Handle both array and object response formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "records" in data:
                    return data["records"]
                else:
                    logger.warning(f"Unexpected response format: {data}")
                    return []

        except httpx.ConnectError:
            logger.warning(f"Could not connect to offline bridge at {url}")
            return []
        except httpx.TimeoutException:
            logger.warning(f"Timeout connecting to offline bridge at {url}")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching offline records: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching offline records: {e}")
            return []

    async def ingest_record(
        self,
        db: AsyncSession,
        record: dict
    ) -> Optional[Incident]:
        """
        Ingest a single offline SMS record into PostgreSQL and trigger agent dispatch.

        Args:
            db: Async database session
            record: Parsed SMS record dictionary

        Returns:
            Created Incident or None if duplicate/invalid
        """
        # Extract record fields
        record_id = record.get("id")
        emergency_type = record.get("emergency_type", "OTHER").upper()
        victim_status = record.get("victim_status", "NEED_EVACUATION").upper()
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        raw_text = record.get("raw_text", "")
        sender = record.get("sender", "unknown")
        confidence = record.get("confidence", 0.0)

        # Deduplication check
        incident_number_pattern = f"RESQ-2026-SMS-{record_id}"
        result = await db.execute(
            select(Incident).where(Incident.incident_number == incident_number_pattern)
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Skipping duplicate SMS record {record_id}")
            return None

        # Map emergency type to hazard
        hazard_map = {
            "FLOOD": "FLOOD",
            "FIRE": "FIRE",
            "COLLAPSE": "COLLAPSED_STRUCTURE",
            "MEDICAL": "MEDICAL_EMERGENCY",
            "OTHER": "OTHER",
        }
        hazard = hazard_map.get(emergency_type, "OTHER")

        # Determine priority
        critical_types = ["FLOOD", "COLLAPSE", "FIRE"]
        critical_statuses = ["TRAPPED", "UNCONSCIOUS"]
        priority = (
            "CRITICAL"
            if emergency_type in critical_types or victim_status in critical_statuses
            else "HIGH"
        )

        # Map victim status to trapped count
        trapped_count = 1 if victim_status == "TRAPPED" else 0

        # Construct PostGIS geometry
        location_wkt = None
        if latitude and longitude:
            try:
                lat = float(latitude)
                lng = float(longitude)
                # Validate Kerala bounds
                if 8.0 < lat < 13.0 and 74.5 < lng < 77.5:
                    location_wkt = WKTElement(f"POINT({lng} {lat})", srid=4326)
                else:
                    logger.warning(f"Coordinates outside Kerala bounds: {lat}, {lng}")
            except (ValueError, TypeError):
                logger.warning(f"Invalid coordinates: {latitude}, {longitude}")

        # Default district (could be enhanced with reverse geocoding)
        district = "Wayanad"

        # Create incident
        incident = Incident(
            incident_number=incident_number_pattern,
            status="REPORTED",
            priority=priority,
            hazard_type=hazard,
            description=f"[OFFLINE SMS] {raw_text} | Sender: {sender} | Confidence: {confidence:.2f}",
            location=location_wkt,
            district=district,
            landmark=None,
            people_affected=1,
            trapped_count=trapped_count,
            injured_count=1 if victim_status in ["INJURED", "UNCONSCIOUS"] else 0,
        )
        db.add(incident)
        await db.flush()  # Get incident.id

        # Record initial status
        await record_status_change(
            db=db,
            entity_type="INCIDENT",
            entity_id=incident.id,
            previous_status=None,
            new_status="REPORTED",
            triggered_by_user_id=None,
            payload={
                "source": "OFFLINE_SMS",
                "raw_sms_id": record_id,
                "emergency_type": emergency_type,
                "victim_status": victim_status,
            }
        )

        # Create tasks
        tasks_created = []

        # Task 1: Rescue extraction (always)
        rescue_task = ResponseTask(
            incident_id=incident.id,
            parent_task_id=None,
            task_type="RESCUE_EXTRACTION",
            status=TaskStatus.PENDING_ASSIGNMENT,
            priority=priority,
            target_location=location_wkt,
            instructions=f"Rescue extraction for {emergency_type} emergency. Victim status: {victim_status}.",
            citizen_confirmed_arrival=False,
        )
        db.add(rescue_task)
        await db.flush()

        await record_status_change(
            db=db,
            entity_type="TASK",
            entity_id=rescue_task.id,
            previous_status=None,
            new_status=TaskStatus.PENDING_ASSIGNMENT,
            triggered_by_user_id=None,
            payload={"task_type": "RESCUE_EXTRACTION", "source": "OFFLINE_SMS"}
        )
        tasks_created.append(rescue_task)

        # Task 2: Hospital admission (for medical emergencies)
        needs_hospital = (
            emergency_type == "MEDICAL"
            or victim_status in ["INJURED", "UNCONSCIOUS"]
        )

        hospital_task = None
        if needs_hospital:
            hospital_task = ResponseTask(
                incident_id=incident.id,
                parent_task_id=rescue_task.id,
                task_type="HOSPITAL_ADMISSION",
                status=TaskStatus.PENDING_ASSIGNMENT,
                priority=priority,
                target_location=location_wkt,
                instructions=f"Hospital admission required for {victim_status} victim.",
                citizen_confirmed_arrival=False,
            )
            db.add(hospital_task)
            await db.flush()

            await record_status_change(
                db=db,
                entity_type="TASK",
                entity_id=hospital_task.id,
                previous_status=None,
                new_status=TaskStatus.PENDING_ASSIGNMENT,
                triggered_by_user_id=None,
                payload={"task_type": "HOSPITAL_ADMISSION", "source": "OFFLINE_SMS"}
            )
            tasks_created.append(hospital_task)

        # Create tracking token (48h expiry)
        tracking_token = TrackingToken(
            incident_id=incident.id,
            token=f"sms-{record_id}-{incident.id.hex[:8]}",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        db.add(tracking_token)

        # Commit transaction
        await db.commit()
        await db.refresh(incident)
        for task in tasks_created:
            await db.refresh(task)

        logger.info(f"Created incident {incident.incident_number} from SMS record {record_id}")

        # === Autonomous Agent Execution ===
        # Dispatch rescue task to nearest organization
        try:
            await dispatch_task(rescue_task, db)
            logger.info(f"Dispatched rescue task {rescue_task.id} via TaskDispatchAgent")
        except Exception as e:
            logger.error(f"Failed to dispatch rescue task: {e}")

        # Route hospital task if needed
        if hospital_task and latitude and longitude:
            try:
                lat = float(latitude)
                lng = float(longitude)
                await route_to_hospital(hospital_task, db, lat, lng)
                logger.info(f"Routed hospital task {hospital_task.id} via HospitalRoutingAgent")
            except Exception as e:
                logger.error(f"Failed to route hospital task: {e}")

        return incident
