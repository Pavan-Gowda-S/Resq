"""
Test cases for typed API client.
"""
import pytest
from agents.core.client import ResqApiClient
from shared.schemas import (
    IncidentReportCreate,
    IncidentReportResponse,
    TaskProposalsPayload,
    ResponseTaskProposal,
    GeoPoint
)
from shared.constants import TaskType, UrgencyPriority


@pytest.fixture
async def api_client():
    """Create API client instance."""
    client = ResqApiClient()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_client_initialization(api_client):
    """Verify client initializes correctly."""
    assert api_client.use_mock == True
    assert api_client.base_url == "http://localhost:8000/api/v1"
    assert api_client._mock_service is not None


@pytest.mark.asyncio
async def test_client_report_incident(api_client):
    """Test incident reporting through client."""
    report = IncidentReportCreate(
        reporter_name="Integration Test User",
        reporter_phone="+919876543210",
        description="Integration test emergency",
        location=GeoPoint(
            type="Point",
            coordinates=[76.3312, 10.3120]
        ),
        district="Thrissur",
        people_affected=3
    )

    response = await api_client.report_incident(report)

    assert isinstance(response, IncidentReportResponse)
    assert response.incident_id is not None
    assert response.tracking_token.startswith("trk_")
    assert "RESQ-2026" in response.incident_number


@pytest.mark.asyncio
async def test_client_check_duplicates(api_client):
    """Test duplicate checking through client."""
    duplicates = await api_client.check_duplicates(
        lat=10.3120,
        lng=76.3312,
        radius_m=150
    )

    assert isinstance(duplicates, list)


@pytest.mark.asyncio
async def test_client_propose_tasks(api_client):
    """Test task proposal through client."""
    # First create incident
    report = IncidentReportCreate(
        description="Multi-task scenario",
        district="Ernakulam",
        people_affected=2
    )

    incident_response = await api_client.report_incident(report)

    # Propose tasks
    payload = TaskProposalsPayload(
        proposals=[
            ResponseTaskProposal(
                task_type=TaskType.RESCUE_EXTRACTION,
                priority=UrgencyPriority.CRITICAL,
                target_location=GeoPoint(
                    type="Point",
                    coordinates=[76.3312, 10.3120]
                )
            )
        ]
    )

    result = await api_client.propose_tasks(
        incident_response.incident_id,
        payload
    )

    assert "incident_id" in result
    assert "created_tasks" in result
    assert len(result["created_tasks"]) == 1


@pytest.mark.asyncio
async def test_client_search_hospitals(api_client):
    """Test hospital search through client."""
    result = await api_client.search_hospitals(
        lat=10.1960,
        lng=76.3860,
        radius_km=25
    )

    assert "count" in result
    assert "results" in result
    assert isinstance(result["results"], list)


@pytest.mark.asyncio
async def test_client_search_hospitals_with_filters(api_client):
    """Test hospital search with capacity filters."""
    result = await api_client.search_hospitals(
        lat=10.1960,
        lng=76.3860,
        min_icu_available=1,
        min_emergency_available=1
    )

    assert "count" in result
    for hospital in result["results"]:
        assert hospital["available_icu_beds"] >= 1
        assert hospital["available_emergency_beds"] >= 1


@pytest.mark.asyncio
async def test_client_get_rescue_teams(api_client):
    """Test rescue team search through client."""
    result = await api_client.get_rescue_teams(
        status="AVAILABLE"
    )

    assert "count" in result
    assert "results" in result
    assert isinstance(result["results"], list)


@pytest.mark.asyncio
async def test_client_create_reservation(api_client):
    """Test resource reservation through client."""
    reservation = await api_client.create_reservation(
        task_id="task-integration-test-001",
        organization_id="org_hospital_b",
        resource_type="HOSPITAL_ICU_BED",
        quantity=1,
        lock_duration_minutes=30
    )

    assert "reservation_id" in reservation
    assert reservation["task_id"] == "task-integration-test-001"
    assert reservation["status"] == "HOLD"


@pytest.mark.asyncio
async def test_client_sync_events(api_client):
    """Test offline event sync through client."""
    events = [
        {
            "event_id": "evt-integration-001",
            "entity_type": "TASK",
            "entity_id": "task-123",
            "action": "UPDATE_STATUS",
            "payload": {"status": "COMPLETED"},
            "client_timestamp": "2026-10-31T08:00:00Z"
        }
    ]

    result = await api_client.sync_events(
        device_id="dev_integration_test",
        events=events
    )

    assert result["synced_count"] == 1
    assert result["rejected_count"] == 0


@pytest.mark.asyncio
async def test_client_connection_cleanup(api_client):
    """Test proper cleanup of HTTP client."""
    # Make a request
    await api_client.check_duplicates(10.0, 76.0)

    # Close client
    await api_client.close()

    # Verify closed
    assert api_client._http_client is None
