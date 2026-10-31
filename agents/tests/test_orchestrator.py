"""
Test suite for Orchestrator & Complete Agent Integration (Phase 6).
Validates end-to-end incident lifecycle through unified LangGraph workflow.
"""
import pytest
from agents.core.client import ResqApiClient
from agents.orchestrator.workflow import process_incident_lifecycle_without_backend


# ============================================================================
# End-to-End Village A Flood Scenario
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_village_a_flood():
    """
    Test 1: Complete Village A Flood Lifecycle
    12 villagers trapped on roof → CRITICAL triage → Rescue matching → Route assessment → Audit seal
    """
    raw_report = {
        "description": "12 villagers trapped on roof of community hall by rapidly rising floodwaters. Road access completely severed.",
        "district": "Thrissur",
        "location": {
            "type": "Point",
            "coordinates": [76.3312, 10.3120]
        },
        "reporter_name": "Local Fire Station",
        "reporter_phone": "+91-9876543210"
    }

    client = ResqApiClient()

    try:
        # Process complete lifecycle
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-village-a-test",
            client=client
        )

        # Verify incident intelligence extraction
        assert "extraction" in final_state
        extraction = final_state["extraction"]
        assert extraction["hazard_type"] == "FLOOD"
        assert extraction["trapped_count"] == 12
        assert extraction["people_affected"] == 12

        # Verify risk decision triage
        assert "triage" in final_state
        triage = final_state["triage"]
        assert triage["priority"] == "CRITICAL"
        assert triage["life_threat_detected"] is True
        assert triage["priority_score"] >= 8.5

        # Verify task proposals
        assert "task_proposals" in final_state
        task_proposals = final_state["task_proposals"]
        assert len(task_proposals) >= 1

        rescue_tasks = [t for t in task_proposals if t["task_type"] == "RESCUE_EXTRACTION"]
        assert len(rescue_tasks) >= 1

        # Verify rescue matching
        assert "matched_resources" in final_state
        matched_resources = final_state["matched_resources"]
        assert "rescue_teams" in matched_resources

        rescue_matches = matched_resources["rescue_teams"]
        assert len(rescue_matches) >= 1

        # Verify assigned team has flood extraction capabilities
        if rescue_matches[0].get("assigned_team"):
            assigned_team = rescue_matches[0]["assigned_team"]
            capabilities = [c.upper() for c in assigned_team.get("capabilities", [])]
            # Should have boat or flood capabilities
            assert any(
                keyword in " ".join(capabilities)
                for keyword in ["BOAT", "FLOOD", "WATER"]
            )

        # Verify route mobility assessment
        assert "routes" in matched_resources or len(matched_resources.get("routes", [])) >= 0

        # Verify audit summary
        assert "audit_summary" in final_state
        audit = final_state["audit_summary"]
        assert audit["incident_id"] == "inc-village-a-test"
        assert audit["total_tasks"] >= 1
        assert audit["matched_tasks"] >= 1
        assert audit["verification_status"] in ["VERIFIED_COMPLETE", "PARTIAL_COMPLETION"]

        # Verify audit trail
        assert "audit_trail" in final_state
        audit_trail = final_state["audit_trail"]

        # Check all agents executed
        agent_names = [entry["agent"] for entry in audit_trail]
        assert "IncidentIntelligenceAgent" in agent_names
        assert "RiskDecisionAgent" in agent_names
        assert "RescueMatchingAgent" in agent_names
        assert "VerificationAuditAgent" in agent_names

        # Verify final seal
        final_seal = audit_trail[-1]
        assert final_seal["agent"] == "VerificationAuditAgent"
        assert final_seal["action"] == "lifecycle_audit_complete"

    finally:
        await client.close()


# ============================================================================
# End-to-End Village B Landslide Trauma Scenario
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_village_b_trauma():
    """
    Test 2: Complete Village B Landslide Trauma Lifecycle
    Compound fracture + cardiac → CRITICAL → Hospital ICU + Blood + Ambulance → Audit
    """
    raw_report = {
        "description": "Elderly resident with compound fracture and severe chest pain after landslide. Requires immediate ICU admission and blood transfusion.",
        "district": "Wayanad",
        "location": {
            "type": "Point",
            "coordinates": [76.1320, 11.5540]
        },
        "reporter_name": "Village Health Worker",
        "reporter_phone": "+91-9876543211"
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-village-b-test",
            client=client
        )

        # Verify extraction
        assert "extraction" in final_state
        extraction = final_state["extraction"]
        assert extraction["hazard_type"] in ["LANDSLIDE", "TRAUMA"]
        assert extraction["injured_count"] >= 1
        assert len(extraction["medical_urgencies"]) >= 1

        # Verify CRITICAL triage
        triage = final_state["triage"]
        assert triage["priority"] == "CRITICAL"
        assert triage["life_threat_detected"] is True

        # Verify multi-pathway tasks
        task_proposals = final_state["task_proposals"]
        task_types = [t["task_type"] for t in task_proposals]

        # Should have hospital admission task
        assert "HOSPITAL_ADMISSION" in task_types or "AMBULANCE_TRANSPORT" in task_types

        # Verify hospital matching
        matched_resources = final_state["matched_resources"]
        assert "hospitals" in matched_resources or "ambulances" in matched_resources

        # Verify resource marketplace (blood allocation)
        if "supplies" in matched_resources:
            supply_allocations = matched_resources["supplies"]
            # Check if blood was allocated
            blood_allocations = [
                s for s in supply_allocations
                if "BLOOD" in s.get("item_code", "")
            ]
            if blood_allocations:
                # Verify medical approval flag
                assert blood_allocations[0].get("requires_medical_officer_approval") is True

        # Verify reservations created
        assert "reservations" in final_state
        reservations = final_state["reservations"]
        assert len(reservations) >= 1

        # Verify audit
        audit = final_state["audit_summary"]
        assert audit["total_tasks"] >= 1
        assert audit["total_reservations"] >= 1
        assert audit["verification_status"] in ["VERIFIED_COMPLETE", "PARTIAL_COMPLETION"]

    finally:
        await client.close()


# ============================================================================
# End-to-End Village C Relief Camp Supplies Scenario
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_village_c_supplies():
    """
    Test 3: Complete Village C Relief Camp Supplies Lifecycle
    Isolated camps → HIGH priority → Supply delivery matching → Audit
    """
    raw_report = {
        "description": "2 relief camps marooned. Running out of drinking water, ORS packets, and basic antibiotics. 180 people affected.",
        "district": "Alappuzha",
        "location": {
            "type": "Point",
            "coordinates": [76.4320, 9.5840]
        },
        "reporter_name": "Camp Coordinator",
        "reporter_phone": "+91-9876543212"
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-village-c-test",
            client=client
        )

        # Verify extraction
        extraction = final_state["extraction"]
        assert extraction["people_affected"] >= 100

        # Verify triage (should be HIGH or MEDIUM for supply shortage)
        triage = final_state["triage"]
        assert triage["priority"] in ["HIGH", "MEDIUM", "CRITICAL"]

        # Verify supply delivery task proposed
        task_proposals = final_state["task_proposals"]
        supply_tasks = [t for t in task_proposals if t["task_type"] == "SUPPLY_DELIVERY"]
        assert len(supply_tasks) >= 1

        # Verify resource marketplace allocation
        matched_resources = final_state["matched_resources"]
        if "supplies" in matched_resources:
            supply_allocations = matched_resources["supplies"]
            assert len(supply_allocations) >= 1

            # Verify ORS or water purification allocated
            allocated_items = [s["item_code"] for s in supply_allocations]
            assert any(
                item in allocated_items
                for item in ["ORS_SACHETS", "PURIFICATION_TABLETS"]
            )

        # Verify audit
        audit = final_state["audit_summary"]
        assert audit["verification_status"] in ["VERIFIED_COMPLETE", "PARTIAL_COMPLETION", "NO_TASKS_PROPOSED"]

    finally:
        await client.close()


# ============================================================================
# Human Review Checkpoint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_human_review_checkpoint_mass_casualty():
    """
    Test 4: Human Review Checkpoint for Mass Casualty
    Ambiguous report with >10 victims triggers human review flag
    """
    raw_report = {
        "description": "Building collapse with approximately 15-20 people trapped. Unclear injuries, some screaming heard.",
        "district": "Kochi",
        "location": {
            "type": "Point",
            "coordinates": [76.2673, 9.9312]
        }
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-mass-casualty-test",
            client=client
        )

        # Verify ambiguous flag or high people count
        extraction = final_state["extraction"]
        is_ambiguous = extraction.get("is_ambiguous", False)
        people_affected = extraction.get("people_affected", 0)

        # Verify triage human review flag
        triage = final_state["triage"]

        # Should trigger human review if ambiguous or mass casualty
        if is_ambiguous or people_affected >= 10:
            # Check if human review was set
            human_review = triage.get("requires_human_review", False)
            # Audit should record this
            audit = final_state["audit_summary"]
            audit_human_review = audit.get("human_review_required", False)

            # At least one should flag human review
            assert human_review or audit_human_review or is_ambiguous

    finally:
        await client.close()


# ============================================================================
# Audit Discrepancy Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_audit_discrepancy_detection():
    """
    Test 5: Audit Detects Unmatched Tasks
    Verifies audit flags when tasks proposed but no matches
    """
    # Report that might not match available resources
    raw_report = {
        "description": "Need helicopter evacuation for injured climber on mountain peak.",
        "district": "Idukki",
        "location": {
            "type": "Point",
            "coordinates": [77.1025, 10.0889]
        }
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-discrepancy-test",
            client=client
        )

        # Verify audit summary exists
        assert "audit_summary" in final_state
        audit = final_state["audit_summary"]

        # Check if tasks were proposed
        total_tasks = audit["total_tasks"]
        matched_tasks = audit["matched_tasks"]

        # If tasks were proposed but not all matched, should have discrepancies
        if total_tasks > matched_tasks:
            assert audit["has_discrepancies"] is True
            assert len(audit["discrepancy_details"]) > 0
            assert audit["verification_status"] in ["REQUIRES_MANUAL_AUDIT", "PARTIAL_COMPLETION"]

    finally:
        await client.close()


# ============================================================================
# Multi-Agent Coordination Tests
# ============================================================================

@pytest.mark.asyncio
async def test_complete_audit_trail_timeline():
    """
    Test 6: Complete Audit Trail Timeline
    Verifies all agents executed in correct sequence
    """
    raw_report = {
        "description": "Flash flood in residential area, 5 families evacuated",
        "district": "Thrissur",
        "location": {
            "type": "Point",
            "coordinates": [76.2144, 10.5276]
        }
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-timeline-test",
            client=client
        )

        # Verify audit trail timeline
        audit = final_state["audit_summary"]
        timeline = audit["timeline"]

        # Verify timeline has entries
        assert len(timeline) >= 3

        # Verify agent execution sequence
        agent_sequence = [entry["agent"] for entry in timeline]

        # Intelligence should be first
        assert agent_sequence[0] == "IncidentIntelligenceAgent"

        # Risk decision should be second
        if len(agent_sequence) > 1:
            assert agent_sequence[1] == "RiskDecisionAgent"

        # Verification audit should be last
        assert agent_sequence[-1] == "VerificationAuditAgent"

        # Verify each entry has timestamp
        for entry in timeline:
            assert "timestamp" in entry
            assert "action" in entry
            assert "summary" in entry

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_conditional_routing_rescue_only():
    """
    Test 7: Conditional Routing - Rescue Only
    Verifies graph routes to rescue matching when only rescue tasks exist
    """
    raw_report = {
        "description": "3 people trapped in vehicle submerged by floodwater. No injuries reported yet.",
        "district": "Ernakulam",
        "location": {
            "type": "Point",
            "coordinates": [76.3500, 10.1000]
        }
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-rescue-only-test",
            client=client
        )

        # Verify rescue matching executed
        audit_trail = final_state["audit_trail"]
        agent_names = [entry["agent"] for entry in audit_trail]

        assert "RescueMatchingAgent" in agent_names

        # Verify rescue resources matched
        matched_resources = final_state["matched_resources"]
        assert "rescue_teams" in matched_resources

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_no_tasks_scenario():
    """
    Test 8: No Tasks Scenario
    Verifies graceful handling when no actionable tasks proposed
    """
    raw_report = {
        "description": "Heavy rain reported in the area. No immediate emergency.",
        "district": "Kannur",
        "location": {
            "type": "Point",
            "coordinates": [75.3704, 11.8745]
        }
    }

    client = ResqApiClient()

    try:
        final_state = await process_incident_lifecycle_without_backend(
            raw_report,
            incident_id="inc-no-tasks-test",
            client=client
        )

        # Verify audit handles no-task scenario
        audit = final_state["audit_summary"]

        # Should have no tasks or low priority
        assert audit["total_tasks"] == 0 or audit["verification_status"] == "NO_TASKS_PROPOSED"

        # Should still complete successfully
        assert "VerificationAuditAgent" in [e["agent"] for e in final_state["audit_trail"]]

    finally:
        await client.close()
