"""
End-to-end integration test verifying that the AI Agent client (ResqApiClient)
with USE_MOCK_BACKEND=False communicates directly with the live FastAPI backend routes.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4

from backend.app.main import app
from backend.app.models.hospital_capacity import HospitalCapacity


@pytest.mark.asyncio
async def test_agent_client_live_backend_workflow(db_session, test_organization):
    """
    Simulate the exact API calls made by the AI Agents against the live FastAPI app.
    """
    # Create HospitalCapacity for test_organization so hospital search and reservation find it
    capacity = HospitalCapacity(
        organization_id=test_organization.id,
        total_emergency_beds=50,
        occupied_emergency_beds=10,
        reserved_emergency_beds=5,
        out_of_service_emergency_beds=2,
        total_icu_beds=20,
        occupied_icu_beds=5,
        reserved_icu_beds=2,
        out_of_service_icu_beds=1,
        has_oxygen_facility=True,
        has_trauma_center=True
    )
    db_session.add(capacity)
    db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test/api/v1",
        headers={
            "Authorization": "Bearer resq_agent_internal_secret_token",
            "Content-Type": "application/json"
        }
    ) as client:

        # 1. Citizen SOS Report
        report_data = {
            "reporter_name": "Suresh Kumar",
            "reporter_phone": "+919847012345",
            "description": "Severe flooding in Aluva town, family stranded on rooftop near bridge.",
            "location": {"type": "Point", "coordinates": [76.3533, 10.1076]},
            "district": "Ernakulam",
            "landmark": "Near Aluva Railway Station",
            "people_affected": 4,
            "source": "WEB_ANONYMOUS"
        }

        resp = await client.post("/incidents/report", json=report_data)
        assert resp.status_code == 201
        report_res = resp.json()
        incident_id = report_res["incident_id"]
        assert report_res["incident_number"].startswith("RESQ-")
        assert "tracking_token" in report_res

        # 2. Duplicate Detection (Spatial PostGIS query)
        dup_resp = await client.get(
            "/incidents/duplicates",
            params={"lat": 10.1076, "lng": 76.3533, "radius_m": 500}
        )
        assert dup_resp.status_code == 200
        duplicates = dup_resp.json()
        assert len(duplicates) >= 1
        assert any(d["incident_id"] == incident_id for d in duplicates)

        # 3. Propose Tasks (POST /incidents/{id}/tasks/propose)
        proposals_payload = {
            "proposals": [
                {
                    "task_type": "RESCUE_EXTRACTION",
                    "priority": "CRITICAL",
                    "target_location": {"type": "Point", "coordinates": [76.3533, 10.1076]},
                    "instructions": "Extract 4 stranded individuals via motorized boat."
                },
                {
                    "task_type": "HOSPITAL_ADMISSION",
                    "priority": "HIGH",
                    "target_location": {"type": "Point", "coordinates": [76.3533, 10.1076]},
                    "instructions": "Admit elderly patient with cardiac condition."
                }
            ]
        }

        tasks_resp = await client.post(
            f"/incidents/{incident_id}/tasks/propose",
            json=proposals_payload
        )
        assert tasks_resp.status_code == 201
        tasks_data = tasks_resp.json()
        assert len(tasks_data["created_tasks"]) == 2
        extraction_task_id = tasks_data["created_tasks"][0]["id"]
        admission_task_id = tasks_data["created_tasks"][1]["id"]

        # 4. Search Rescue Teams (GET /resources/rescue-teams)
        rescue_resp = await client.get("/resources/rescue-teams")
        assert rescue_resp.status_code == 200
        rescue_data = rescue_resp.json()
        assert "results" in rescue_data
        assert rescue_data["count"] > 0

        # 5. Search Hospitals (GET /resources/hospitals/search)
        # Search centered near test_organization's location (Ernakulam ~ 10.0, 76.2) with 100km radius
        hosp_resp = await client.get(
            "/resources/hospitals/search",
            params={"lat": 9.9816, "lng": 76.2999, "radius_km": 100}
        )
        assert hosp_resp.status_code == 200
        hosp_data = hosp_resp.json()
        assert "results" in hosp_data
        assert hosp_data["count"] > 0
        assert any(h["organization_id"] == str(test_organization.id) for h in hosp_data["results"])

        # 6. Create Atomic Bed Reservation
        res_payload = {
            "task_id": admission_task_id,
            "organization_id": str(test_organization.id),
            "resource_type": "HOSPITAL_EMERGENCY_BED",
            "quantity": 1,
            "lock_duration_minutes": 30
        }
        res_resp = await client.post("/resources/reservations", json=res_payload)
        assert res_resp.status_code == 201
        res_data = res_resp.json()
        assert res_data["status"] == "HOLD"
        assert res_data["quantity"] == 1
        assert "reservation_id" in res_data

        # 7. Offline Event Sync (POST /sync/events)
        sync_payload = {
            "device_id": "test_boat_01",
            "events": [
                {
                    "event_id": str(uuid4()),
                    "entity_type": "TASK",
                    "entity_id": extraction_task_id,
                    "action": "UPDATE_STATUS",
                    "payload": {"status": "EN_ROUTE"},
                    "client_timestamp": "2026-10-31T12:00:00Z"
                }
            ]
        }
        sync_resp = await client.post("/sync/events", json=sync_payload)
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["synced_count"] == 1
        assert sync_data["rejected_count"] == 0
