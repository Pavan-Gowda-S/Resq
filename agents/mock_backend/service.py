"""
Contract-Compliant Mock Backend Service.
In-memory asynchronous API implementation for testing without live backend.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from uuid import uuid4

from shared.schemas import (
    IncidentReportCreate,
    IncidentReportResponse,
    TaskProposalsPayload,
    GeoPoint
)
from shared.constants import IncidentStatus, TaskStatus


class MockBackendService:
    """
    Mock backend service providing contract-compliant responses.
    Loads seed data from simulation and maintains in-memory state.
    """

    def __init__(self):
        self.incidents: Dict[str, Dict[str, Any]] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.reservations: Dict[str, Dict[str, Any]] = {}
        self._synced_events: List[Dict[str, Any]] = []
        self._seed_data: Optional[Dict[str, Any]] = None
        self._load_seed_data()

    def _load_seed_data(self):
        """Load Kerala flood simulation seed data."""
        seed_path = Path(__file__).parent.parent.parent / "simulation" / "seed_data" / "kerala_seed.json"
        if seed_path.exists():
            with open(seed_path, "r", encoding="utf-8") as f:
                self._seed_data = json.load(f)
        else:
            # Fallback minimal seed data
            self._seed_data = {
                "hospitals": [
                    {
                        "id": "org_hospital_a",
                        "name": "Hospital A - General Medical Center",
                        "location": {"type": "Point", "coordinates": [76.3860, 10.1960]},
                        "capacity": {
                            "available_emergency_beds": 4,
                            "available_icu_beds": 0
                        }
                    },
                    {
                        "id": "org_hospital_b",
                        "name": "Hospital B - Specialty Cardiac & Trauma Institute",
                        "location": {"type": "Point", "coordinates": [76.2999, 9.9816]},
                        "capacity": {
                            "available_emergency_beds": 1,
                            "available_icu_beds": 2
                        }
                    }
                ],
                "rescue_teams": [],
                "ambulances": []
            }

    async def report_incident(self, data: IncidentReportCreate) -> IncidentReportResponse:
        """
        POST /api/v1/incidents/report
        Create new incident report.
        """
        incident_id = str(uuid4())
        incident_number = f"RESQ-2026-{len(self.incidents) + 1:04d}"
        tracking_token = f"trk_{uuid4().hex[:22]}"

        incident_record = {
            "id": incident_id,
            "incident_number": incident_number,
            "status": IncidentStatus.REPORTED.value,
            "tracking_token": tracking_token,
            "report_data": data.model_dump(),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "tasks": []
        }

        self.incidents[incident_id] = incident_record

        return IncidentReportResponse(
            incident_id=incident_id,
            incident_number=incident_number,
            status=IncidentStatus.REPORTED,
            tracking_token=tracking_token,
            tracking_url=f"https://resq.org/track/{tracking_token}",
            message="Emergency report acknowledged. Intelligent triage has been initiated."
        )

    async def check_duplicates(
        self,
        lat: float,
        lng: float,
        radius_m: int = 200
    ) -> List[Dict[str, Any]]:
        """
        GET /api/v1/incidents/duplicates
        Find nearby incidents within radius.
        """
        # Simple mock: return empty list (no duplicates)
        # In real implementation, would do spatial query
        return []

    async def propose_tasks(
        self,
        incident_id: str,
        payload: TaskProposalsPayload
    ) -> Dict[str, Any]:
        """
        POST /api/v1/incidents/{incident_id}/tasks/propose
        Create linked response tasks.
        """
        # Auto-create incident record if missing (for testing)
        if incident_id not in self.incidents:
            self.incidents[incident_id] = {
                "id": incident_id,
                "status": "UNDER_RESPONSE",
                "tasks": []
            }

        created_tasks = []

        for proposal in payload.proposals:
            task_id = str(uuid4())
            task = {
                "id": task_id,
                "incident_id": incident_id,
                "task_type": proposal.task_type.value,
                "priority": proposal.priority.value,
                "status": TaskStatus.PENDING_ASSIGNMENT.value,
                "target_location": proposal.target_location.model_dump(),
                "instructions": proposal.instructions,
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            self.tasks[task_id] = task
            created_tasks.append({
                "id": task_id,
                "task_type": proposal.task_type.value,
                "status": TaskStatus.PENDING_ASSIGNMENT.value
            })

            # Link to incident
            self.incidents[incident_id]["tasks"].append(task_id)

        return {
            "incident_id": incident_id,
            "created_tasks": created_tasks
        }

    async def search_hospitals(
        self,
        lat: float,
        lng: float,
        radius_km: Optional[float] = None,
        min_icu_available: Optional[int] = None,
        min_emergency_available: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        GET /api/v1/resources/hospitals/search
        Search for hospitals by location and capacity.
        """
        hospitals = self._seed_data.get("hospitals", [])

        # Simple mock filtering
        results = []
        for hospital in hospitals:
            hosp_data = {
                "organization_id": hospital["id"],
                "hospital_name": hospital["name"],
                "distance_km": 6.4,  # Mock distance
                "available_emergency_beds": hospital["capacity"]["available_emergency_beds"],
                "available_icu_beds": hospital["capacity"]["available_icu_beds"],
                "has_trauma_center": True
            }

            # Apply filters
            if min_icu_available is not None:
                if hosp_data["available_icu_beds"] < min_icu_available:
                    continue

            if min_emergency_available is not None:
                if hosp_data["available_emergency_beds"] < min_emergency_available:
                    continue

            results.append(hosp_data)

        return {
            "count": len(results),
            "results": results
        }

    async def get_rescue_teams(
        self,
        capability: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        status: str = "AVAILABLE"
    ) -> Dict[str, Any]:
        """
        GET /api/v1/resources/rescue-teams
        Search for available rescue teams.
        """
        rescue_teams = self._seed_data.get("rescue_teams", [])

        # Filter by status
        available_teams = [
            team for team in rescue_teams
            if team.get("status", "AVAILABLE") == status
        ]

        return {
            "count": len(available_teams),
            "results": available_teams
        }

    async def create_reservation(
        self,
        task_id: str,
        organization_id: str,
        resource_type: str,
        quantity: int,
        lock_duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        POST /api/v1/resources/reservations
        Create atomic resource reservation.
        """
        reservation_id = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(minutes=lock_duration_minutes)

        reservation = {
            "reservation_id": reservation_id,
            "task_id": task_id,
            "organization_id": organization_id,
            "resource_type": resource_type,
            "quantity": quantity,
            "status": "HOLD",
            "expires_at": expires_at.isoformat() + "Z",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

        self.reservations[reservation_id] = reservation

        return reservation

    async def sync_events(
        self,
        device_id: str,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        POST /api/v1/sync/events
        Synchronize offline events.
        """
        synced_count = 0
        rejected_count = 0
        conflicts = []

        for event in events:
            # Mock: accept all events
            self._synced_events.append({
                "device_id": device_id,
                "event": event,
                "synced_at": datetime.utcnow().isoformat() + "Z"
            })
            synced_count += 1

        return {
            "synced_count": synced_count,
            "rejected_count": rejected_count,
            "conflicts": conflicts
        }

    async def search_inventory(
        self,
        item_code: Optional[str] = None,
        min_quantity: int = 1
    ) -> Dict[str, Any]:
        """
        GET /api/v1/resources/inventory/search
        Search supplier inventory for available medical supplies and blood units.

        Args:
            item_code: Optional specific item code filter
            min_quantity: Minimum quantity threshold

        Returns:
            List of supplier organizations with matching inventory
        """
        await asyncio.sleep(0.01)

        if not self._seed_data or "suppliers" not in self._seed_data:
            return {"suppliers": []}

        matching_suppliers = []

        for supplier in self._seed_data["suppliers"]:
            supplier_inventory = []

            for item in supplier.get("inventory", []):
                # Filter by item code if specified
                if item_code and item["item_code"] != item_code:
                    continue

                # Filter by minimum quantity
                if item["quantity"] < min_quantity:
                    continue

                supplier_inventory.append({
                    "item_code": item["item_code"],
                    "available_quantity": item["quantity"]
                })

            # Include supplier if they have matching inventory
            if supplier_inventory:
                matching_suppliers.append({
                    "organization_id": supplier["id"],
                    "organization_name": supplier["name"],
                    "organization_type": supplier["type"],
                    "location": supplier["location"],
                    "inventory": supplier_inventory
                })

        return {
            "suppliers": matching_suppliers,
            "result_count": len(matching_suppliers)
        }
