"""
Test cases for mock backend service.
"""
import pytest
import asyncio
from agents.mock_backend.service import MockBackendService
from shared.schemas import (
    IncidentReportCreate,
    IncidentReportResponse,
    TaskProposalsPayload,
    ResponseTaskProposal,
    GeoPoint
)
from shared.constants import IncidentStatus, TaskType, UrgencyPriority, TaskStatus


@pytest.fixture
def mock_backend():
    """Create mock backend service instance."""
    return MockBackendService()


@pytest.mark.asyncio
async def test_report_incident(mock_backend):
    """Test incident report creation."""
    report = IncidentReportCreate(
        reporter_name="Test User",
        reporter_phone="+919876543210",
        description="Test emergency situation",
        location=GeoPoint(
            type="Point",
            coordinates=[76.2144, 10.5276]
        ),
        district="Thrissur",
        landmark="Test landmark",
        people_affected=4,
        source="WEB_ANONYMOUS"
    )

    response = await mock_backend.report_incident(report)

    assert isinstance(response, IncidentReportResponse)
    assert response.status == IncidentStatus.REPORTED
    assert response.incident_id is not None
    assert response.tracking_token.startswith("trk_")
    assert "RESQ-2026" in response.incident_number
    assert "acknowledged" in response.message.lower()


@pytest.mark.asyncio
async def test_check_duplicates(mock_backend):
    """Test duplicate incident detection."""
    duplicates = await mock_backend.check_duplicates(
        lat=10.5276,
        lng=76.2144,
        radius_m=200
    )

    assert isinstance(duplicates, list)
    # Mock returns empty list (no duplicates)
    assert len(duplicates) == 0


@pytest.mark.asyncio
async def test_propose_tasks(mock_backend):
    """Test task proposal creation."""
    # First create an incident
    report = IncidentReportCreate(
        description="Emergency requiring multiple tasks",
        district="Thrissur",
        people_affected=2
    )

    incident_response = await mock_backend.report_incident(report)
    incident_id = incident_response.incident_id

    # Propose tasks
    payload = TaskProposalsPayload(
        proposals=[
            ResponseTaskProposal(
                task_type=TaskType.RESCUE_EXTRACTION,
                priority=UrgencyPriority.CRITICAL,
                target_location=GeoPoint(
                    type="Point",
                    coordinates=[76.2144, 10.5276]
                ),
                instructions="Rescue trapped victims"
            ),
            ResponseTaskProposal(
                task_type=TaskType.HOSPITAL_ADMISSION,
                priority=UrgencyPriority.HIGH,
                target_location=GeoPoint(
                    type="Point",
                    coordinates=[76.2144, 10.5276]
                ),
                instructions="ICU bed reservation required"
            )
        ]
    )

    result = await mock_backend.propose_tasks(incident_id, payload)

    assert result["incident_id"] == incident_id
    assert len(result["created_tasks"]) == 2
    assert result["created_tasks"][0]["task_type"] == TaskType.RESCUE_EXTRACTION.value
    assert result["created_tasks"][0]["status"] == TaskStatus.PENDING_ASSIGNMENT.value
    assert result["created_tasks"][1]["task_type"] == TaskType.HOSPITAL_ADMISSION.value


@pytest.mark.asyncio
async def test_search_hospitals(mock_backend):
    """Test hospital capacity search."""
    result = await mock_backend.search_hospitals(
        lat=10.1960,
        lng=76.3860,
        radius_km=20
    )

    assert "count" in result
    assert "results" in result
    assert result["count"] >= 2  # Should have Hospital A and B from seed data

    # Check Hospital B has ICU beds
    hospital_b = next(
        (h for h in result["results"] if "Cardiac" in h["hospital_name"]),
        None
    )
    assert hospital_b is not None
    assert hospital_b["available_icu_beds"] == 2


@pytest.mark.asyncio
async def test_search_hospitals_with_filters(mock_backend):
    """Test hospital search with capacity filters."""
    # Filter for hospitals with at least 2 ICU beds
    result = await mock_backend.search_hospitals(
        lat=10.1960,
        lng=76.3860,
        min_icu_available=2
    )

    assert result["count"] >= 1
    for hospital in result["results"]:
        assert hospital["available_icu_beds"] >= 2


@pytest.mark.asyncio
async def test_create_reservation(mock_backend):
    """Test atomic resource reservation."""
    reservation = await mock_backend.create_reservation(
        task_id="task-123",
        organization_id="org_hospital_b",
        resource_type="HOSPITAL_ICU_BED",
        quantity=1,
        lock_duration_minutes=30
    )

    assert reservation["reservation_id"] is not None
    assert reservation["task_id"] == "task-123"
    assert reservation["resource_type"] == "HOSPITAL_ICU_BED"
    assert reservation["quantity"] == 1
    assert reservation["status"] == "HOLD"
    assert "expires_at" in reservation
    assert reservation["expires_at"].endswith("Z")


@pytest.mark.asyncio
async def test_sync_events(mock_backend):
    """Test offline event synchronization."""
    events = [
        {
            "event_id": "evt-001",
            "entity_type": "TASK",
            "entity_id": "task-123",
            "action": "UPDATE_STATUS",
            "payload": {"status": "COMPLETED"},
            "client_timestamp": "2026-10-31T10:00:00Z"
        },
        {
            "event_id": "evt-002",
            "entity_type": "TASK",
            "entity_id": "task-124",
            "action": "UPDATE_STATUS",
            "payload": {"status": "EN_ROUTE"},
            "client_timestamp": "2026-10-31T10:05:00Z"
        }
    ]

    result = await mock_backend.sync_events(
        device_id="dev_boat_team_01",
        events=events
    )

    assert result["synced_count"] == 2
    assert result["rejected_count"] == 0
    assert len(result["conflicts"]) == 0


@pytest.mark.asyncio
async def test_get_rescue_teams(mock_backend):
    """Test rescue team search."""
    result = await mock_backend.get_rescue_teams(
        status="AVAILABLE"
    )

    assert "count" in result
    assert "results" in result
    # Seed data may or may not have rescue teams
    assert isinstance(result["results"], list)
