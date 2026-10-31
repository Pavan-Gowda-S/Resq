"""
RESQ Typed Asynchronous Backend API Client.
Routes requests to mock or live backend with retry logic.
"""
import asyncio
from typing import List, Dict, Any, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from agents.core.config import config
from agents.mock_backend.service import MockBackendService
from shared.schemas import (
    IncidentReportCreate,
    IncidentReportResponse,
    TaskProposalsPayload
)


class ResqApiClient:
    """
    Typed HTTP client for RESQ backend API with automatic retry logic.
    Routes to MockBackendService when USE_MOCK_BACKEND=True.
    """

    def __init__(self):
        self.base_url = config.BACKEND_API_BASE_URL
        self.timeout = config.REQUEST_TIMEOUT_SECONDS
        self.api_key = config.AGENT_SYSTEM_API_KEY
        self.use_mock = config.USE_MOCK_BACKEND

        # Initialize mock backend if enabled
        self._mock_service = MockBackendService() if self.use_mock else None

        # HTTP client for live backend
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self._http_client

    async def close(self):
        """Close HTTP client connection."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True
    )
    async def _make_request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic.
        Retries on 5xx errors and network timeouts.
        """
        client = await self._get_http_client()
        response = await client.request(method, path, **kwargs)

        # Retry on 5xx server errors
        if 500 <= response.status_code < 600:
            raise httpx.HTTPStatusError(
                f"Server error: {response.status_code}",
                request=response.request,
                response=response
            )

        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Incident Management APIs
    # ========================================================================

    async def report_incident(
        self,
        data: IncidentReportCreate
    ) -> IncidentReportResponse:
        """
        POST /api/v1/incidents/report
        Submit new incident report.
        """
        if self.use_mock:
            return await self._mock_service.report_incident(data)

        response_data = await self._make_request(
            "POST",
            "/incidents/report",
            json=data.model_dump()
        )
        return IncidentReportResponse(**response_data)

    async def check_duplicates(
        self,
        lat: float,
        lng: float,
        radius_m: int = 200
    ) -> List[Dict[str, Any]]:
        """
        GET /api/v1/incidents/duplicates
        Check for nearby duplicate incidents.
        """
        if self.use_mock:
            return await self._mock_service.check_duplicates(lat, lng, radius_m)

        response_data = await self._make_request(
            "GET",
            "/incidents/duplicates",
            params={"lat": lat, "lng": lng, "radius_m": radius_m}
        )
        return response_data

    async def propose_tasks(
        self,
        incident_id: str,
        payload: TaskProposalsPayload
    ) -> Dict[str, Any]:
        """
        POST /api/v1/incidents/{incident_id}/tasks/propose
        Create linked response tasks for incident.
        """
        if self.use_mock:
            return await self._mock_service.propose_tasks(incident_id, payload)

        return await self._make_request(
            "POST",
            f"/incidents/{incident_id}/tasks/propose",
            json=payload.model_dump()
        )

    # ========================================================================
    # Resource Discovery APIs
    # ========================================================================

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
        if self.use_mock:
            return await self._mock_service.search_hospitals(
                lat, lng, radius_km, min_icu_available, min_emergency_available
            )

        params = {"lat": lat, "lng": lng}
        if radius_km is not None:
            params["radius_km"] = radius_km
        if min_icu_available is not None:
            params["min_icu_available"] = min_icu_available
        if min_emergency_available is not None:
            params["min_emergency_available"] = min_emergency_available

        return await self._make_request(
            "GET",
            "/resources/hospitals/search",
            params=params
        )

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
        if self.use_mock:
            return await self._mock_service.get_rescue_teams(
                capability, lat, lng, status
            )

        params = {"status": status}
        if capability:
            params["capability"] = capability
        if lat is not None:
            params["lat"] = lat
        if lng is not None:
            params["lng"] = lng

        return await self._make_request(
            "GET",
            "/resources/rescue-teams",
            params=params
        )

    # ========================================================================
    # Reservation & Allocation APIs
    # ========================================================================

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
        Create atomic resource reservation with time-bounded lock.
        """
        if self.use_mock:
            return await self._mock_service.create_reservation(
                task_id, organization_id, resource_type, quantity, lock_duration_minutes
            )

        payload = {
            "task_id": task_id,
            "organization_id": organization_id,
            "resource_type": resource_type,
            "quantity": quantity,
            "lock_duration_minutes": lock_duration_minutes
        }

        return await self._make_request(
            "POST",
            "/resources/reservations",
            json=payload
        )

    # ========================================================================
    # Inventory & Supply Chain APIs
    # ========================================================================

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
        if self.use_mock:
            return await self._mock_service.search_inventory(item_code, min_quantity)

        params = {}
        if item_code:
            params["item_code"] = item_code
        if min_quantity > 1:
            params["min_quantity"] = min_quantity

        return await self._make_request(
            "GET",
            "/resources/inventory/search",
            params=params
        )

    # ========================================================================
    # Offline Synchronization APIs
    # ========================================================================

    async def sync_events(
        self,
        device_id: str,
        events: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        POST /api/v1/sync/events
        Synchronize offline events from field devices.
        """
        if self.use_mock:
            return await self._mock_service.sync_events(device_id, events)

        payload = {
            "device_id": device_id,
            "events": events
        }

        return await self._make_request(
            "POST",
            "/sync/events",
            json=payload
        )
