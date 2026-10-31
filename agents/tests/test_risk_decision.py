"""
Test suite for Risk & Decision Agent.
Validates deterministic triage rules and multi-pathway task generation.
"""
import pytest
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.incident_intelligence.schemas import ExtractedEntities
from agents.risk_decision.triage_rules import evaluate_incident_risk
from agents.risk_decision.pathway_generator import generate_task_pathways
from agents.risk_decision.agent import run_risk_decision
from agents.risk_decision.schemas import TriageResult
from shared.constants import HazardType, UrgencyPriority, TaskType


@pytest.mark.asyncio
async def test_village_a_flood_critical_triage():
    """
    Test 1: Village A Flood Scenario - Critical Multi-Task Generation
    12 trapped villagers on roof in rapidly rising flood zone.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.FLOOD,
        people_affected=12,
        trapped_count=12,
        injured_count=0,
        medical_urgencies=[],
        environmental_hazards=["rising_floodwater"],
        extracted_landmark="Community hall near Chalakudy Bridge",
        missing_critical_info=[],
        confidence_score=0.92,
        is_ambiguous=False,
        summary="12 villagers trapped on community hall roof by rapidly rising floodwaters"
    )

    triage = evaluate_incident_risk(extraction)

    # Verify CRITICAL priority for mass trapped scenario
    assert triage.priority == UrgencyPriority.CRITICAL
    assert triage.priority_score >= 8.5
    assert triage.life_threat_detected == True
    assert "trapped" in triage.clinical_rationale.lower()
    assert "12" in triage.clinical_rationale or "multiple" in triage.clinical_rationale.lower()

    # Generate task proposals
    proposals = generate_task_pathways(extraction, triage, [76.3312, 10.3120])

    # Verify RESCUE_EXTRACTION task generated
    rescue_tasks = [p for p in proposals if p.task_type == TaskType.RESCUE_EXTRACTION]
    assert len(rescue_tasks) >= 1
    assert rescue_tasks[0].priority == UrgencyPriority.CRITICAL
    assert "rescue" in rescue_tasks[0].instructions.lower() or "extraction" in rescue_tasks[0].instructions.lower()


@pytest.mark.asyncio
async def test_village_b_trauma_linked_tasks():
    """
    Test 2: Village B Landslide Trauma - Linked Healthcare & Transit
    Elderly resident with compound fracture and severe chest pain.
    Must generate BOTH ambulance AND hospital admission tasks.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.LANDSLIDE,
        people_affected=4,
        trapped_count=0,
        injured_count=1,
        medical_urgencies=["compound_fracture", "cardiac_symptoms"],
        environmental_hazards=[],
        extracted_landmark="Near Meppadi hills",
        missing_critical_info=[],
        confidence_score=0.88,
        is_ambiguous=False,
        summary="Elderly resident with compound fracture and suspected cardiac symptoms near Meppadi"
    )

    triage = evaluate_incident_risk(extraction)

    # Verify CRITICAL priority for cardiac symptoms
    assert triage.priority == UrgencyPriority.CRITICAL
    assert triage.life_threat_detected == True
    assert triage.requires_human_review == False  # Life threat is certain
    assert "cardiac" in triage.clinical_rationale.lower() or "medical" in triage.clinical_rationale.lower()

    # Generate task proposals
    proposals = generate_task_pathways(extraction, triage, [76.1320, 11.5540])

    # Verify BOTH ambulance AND hospital tasks generated
    ambulance_tasks = [p for p in proposals if p.task_type == TaskType.AMBULANCE_TRANSPORT]
    hospital_tasks = [p for p in proposals if p.task_type == TaskType.HOSPITAL_ADMISSION]

    assert len(ambulance_tasks) >= 1, "Ambulance transport task must be generated"
    assert len(hospital_tasks) >= 1, "Hospital admission task must be generated"

    # Verify both are CRITICAL priority
    assert ambulance_tasks[0].priority == UrgencyPriority.CRITICAL
    assert hospital_tasks[0].priority == UrgencyPriority.CRITICAL

    # Verify instructions mention medical conditions
    assert "cardiac" in hospital_tasks[0].instructions.lower() or "icu" in hospital_tasks[0].instructions.lower()


@pytest.mark.asyncio
async def test_village_c_supply_delivery():
    """
    Test 3: Village C Relief Camp Scenario
    Marooned camps running out of water and medicine.
    Verify SUPPLY_DELIVERY task generated.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.FLOOD,
        people_affected=180,
        trapped_count=0,
        injured_count=0,
        medical_urgencies=[],
        environmental_hazards=[],
        extracted_landmark="Kuttanad relief camps",
        missing_critical_info=[],
        confidence_score=0.85,
        is_ambiguous=False,
        summary="2 relief camps marooned. Running out of drinking water, ORS packets, and basic antibiotics."
    )

    triage = evaluate_incident_risk(extraction)

    # Verify HIGH or MEDIUM priority for supply shortage
    assert triage.priority in [UrgencyPriority.HIGH, UrgencyPriority.MEDIUM]

    # Generate task proposals
    proposals = generate_task_pathways(extraction, triage, [76.4320, 9.5840])

    # Verify SUPPLY_DELIVERY task generated
    supply_tasks = [p for p in proposals if p.task_type == TaskType.SUPPLY_DELIVERY]
    assert len(supply_tasks) >= 1, "Supply delivery task must be generated for isolated camps"

    # Verify instructions mention supplies
    assert any(word in supply_tasks[0].instructions.lower() for word in ["supply", "water", "medicine", "food"])


@pytest.mark.asyncio
async def test_deterministic_cardiac_rule():
    """
    Test 4: Deterministic Rule Invariants
    Cardiac symptoms MUST NEVER produce LOW or MEDIUM priority.
    """
    # Scenario: Single person with cardiac symptoms, no other complications
    extraction = ExtractedEntities(
        hazard_type=HazardType.MEDICAL_EMERGENCY,
        people_affected=1,
        trapped_count=0,
        injured_count=1,
        medical_urgencies=["cardiac_symptoms"],
        environmental_hazards=[],
        extracted_landmark=None,
        missing_critical_info=[],
        confidence_score=0.75,
        is_ambiguous=False,
        summary="Person experiencing severe chest pain and breathing difficulty"
    )

    triage = evaluate_incident_risk(extraction)

    # CRITICAL SAFETY INVARIANT: Cardiac = CRITICAL or HIGH, NEVER LOW/MEDIUM
    assert triage.priority in [UrgencyPriority.CRITICAL, UrgencyPriority.HIGH]
    assert triage.priority != UrgencyPriority.LOW
    assert triage.priority != UrgencyPriority.MEDIUM
    assert triage.life_threat_detected == True


@pytest.mark.asyncio
async def test_severe_bleeding_critical():
    """
    Test deterministic rule for severe bleeding.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.MEDICAL_EMERGENCY,
        people_affected=1,
        trapped_count=0,
        injured_count=1,
        medical_urgencies=["severe_bleeding"],
        environmental_hazards=[],
        extracted_landmark=None,
        missing_critical_info=[],
        confidence_score=0.80,
        is_ambiguous=False,
        summary="Person with arterial bleeding from leg injury"
    )

    triage = evaluate_incident_risk(extraction)

    assert triage.priority == UrgencyPriority.CRITICAL
    assert triage.life_threat_detected == True
    assert triage.priority_score >= 8.5


@pytest.mark.asyncio
async def test_state_integration_with_client():
    """
    Test 5: State Integration & Client Call
    Executes run_risk_decision with mock client, verifying backend task creation.
    """
    # Create state with extraction and incident ID
    state: AgentState = {
        "incident_id": "test-incident-123",
        "raw_report": {
            "description": "12 villagers trapped on roof by floodwaters",
            "district": "Thrissur",
            "location": {
                "type": "Point",
                "coordinates": [76.3312, 10.3120]
            }
        },
        "extraction": {
            "hazard_type": "FLOOD",
            "people_affected": 12,
            "trapped_count": 12,
            "injured_count": 0,
            "medical_urgencies": [],
            "environmental_hazards": ["rising_floodwater"],
            "extracted_landmark": "Community hall",
            "missing_critical_info": [],
            "confidence_score": 0.92,
            "is_ambiguous": False,
            "summary": "12 villagers trapped on roof by rising floodwaters"
        }
    }

    # Run risk decision agent
    client = ResqApiClient()
    try:
        # Create incident in mock service to obtain valid incident_id
        from shared.schemas import IncidentReportCreate, GeoPoint
        incident_res = await client.report_incident(
            IncidentReportCreate(
                description="12 villagers trapped on roof by floodwaters",
                district="Thrissur",
                location=GeoPoint(type="Point", coordinates=[76.3312, 10.3120]),
                people_affected=12
            )
        )
        state["incident_id"] = incident_res.incident_id

        updated_state = await run_risk_decision(state, client)

        # Verify triage populated
        assert "triage" in updated_state
        assert updated_state["triage"]["priority"] == UrgencyPriority.CRITICAL.value
        assert updated_state["triage"]["life_threat_detected"] == True

        # Verify task proposals generated
        assert "task_proposals" in updated_state
        assert len(updated_state["task_proposals"]) >= 1

        # Verify tasks created in backend (via mock)
        assert "created_tasks" in updated_state
        assert len(updated_state["created_tasks"]) >= 1

        # Verify audit trail
        assert "audit_trail" in updated_state
        risk_audit = [e for e in updated_state["audit_trail"] if e["agent"] == "RiskDecisionAgent"]
        assert len(risk_audit) >= 1

        audit_entry = risk_audit[0]
        assert audit_entry["action"] == "triage_and_task_proposal_complete"
        assert "results" in audit_entry
        assert audit_entry["results"]["priority"] == UrgencyPriority.CRITICAL.value
        assert audit_entry["results"]["task_count"] >= 1

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_multi_pathway_generation():
    """
    Test multi-pathway task generation for complex scenario.
    Trapped + Injured should generate: RESCUE + AMBULANCE + HOSPITAL.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.FLOOD,
        people_affected=4,
        trapped_count=4,
        injured_count=1,
        medical_urgencies=["compound_fracture"],
        environmental_hazards=["rising_floodwater"],
        extracted_landmark="Red house with solar panels",
        missing_critical_info=[],
        confidence_score=0.88,
        is_ambiguous=False,
        summary="4 family members trapped on terrace. One has compound fracture from fall."
    )

    triage = evaluate_incident_risk(extraction)
    proposals = generate_task_pathways(extraction, triage, [76.2144, 10.5276])

    # Verify multiple task types generated
    task_types = [p.task_type for p in proposals]

    assert TaskType.RESCUE_EXTRACTION in task_types, "Rescue task required for trapped individuals"
    assert TaskType.AMBULANCE_TRANSPORT in task_types, "Ambulance required for injured person"
    assert TaskType.HOSPITAL_ADMISSION in task_types, "Hospital admission required for fracture"

    # Verify at least 3 tasks for this complex scenario
    assert len(proposals) >= 3


@pytest.mark.asyncio
async def test_ambiguous_report_review_flag():
    """
    Test that ambiguous reports with life threats flag for human review.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.OTHER,
        people_affected=1,
        trapped_count=0,
        injured_count=1,
        medical_urgencies=["cardiac_symptoms"],
        environmental_hazards=[],
        extracted_landmark=None,
        missing_critical_info=["exact_location", "exact_headcount"],
        confidence_score=0.55,
        is_ambiguous=True,
        summary="Someone needs help urgently, chest pain mentioned"
    )

    triage = evaluate_incident_risk(extraction)

    # Should still be CRITICAL due to cardiac symptoms
    assert triage.priority == UrgencyPriority.CRITICAL
    assert triage.life_threat_detected == True

    # Should flag for human review due to ambiguity
    assert triage.requires_human_review == True
    assert len(triage.missing_info_flags) > 0


@pytest.mark.asyncio
async def test_fire_emergency_critical():
    """
    Test that fire emergencies receive CRITICAL priority.
    """
    extraction = ExtractedEntities(
        hazard_type=HazardType.FIRE,
        people_affected=3,
        trapped_count=3,
        injured_count=0,
        medical_urgencies=[],
        environmental_hazards=[],
        extracted_landmark="Apartment building",
        missing_critical_info=[],
        confidence_score=0.95,
        is_ambiguous=False,
        summary="Building fire with 3 people trapped inside"
    )

    triage = evaluate_incident_risk(extraction)

    assert triage.priority == UrgencyPriority.CRITICAL
    assert triage.life_threat_detected == True
    assert triage.priority_score >= 9.0
    assert "fire" in triage.clinical_rationale.lower()


@pytest.mark.asyncio
async def test_priority_score_ranges():
    """
    Test that priority scores fall within expected ranges.
    """
    # LOW priority scenario
    low_extraction = ExtractedEntities(
        hazard_type=HazardType.OTHER,
        people_affected=1,
        trapped_count=0,
        injured_count=0,
        medical_urgencies=[],
        environmental_hazards=[],
        extracted_landmark=None,
        missing_critical_info=[],
        confidence_score=0.70,
        is_ambiguous=False,
        summary="General inquiry about flood situation"
    )

    low_triage = evaluate_incident_risk(low_extraction)
    assert 1.0 <= low_triage.priority_score < 3.5
    assert low_triage.priority == UrgencyPriority.LOW or low_triage.priority == UrgencyPriority.MEDIUM

    # CRITICAL priority scenario
    critical_extraction = ExtractedEntities(
        hazard_type=HazardType.COLLAPSED_STRUCTURE,
        people_affected=8,
        trapped_count=8,
        injured_count=3,
        medical_urgencies=["severe_bleeding", "respiratory_distress"],
        environmental_hazards=[],
        extracted_landmark=None,
        missing_critical_info=[],
        confidence_score=0.90,
        is_ambiguous=False,
        summary="Building collapse with 8 trapped, 3 severely injured"
    )

    critical_triage = evaluate_incident_risk(critical_extraction)
    assert 8.5 <= critical_triage.priority_score <= 10.0
    assert critical_triage.priority == UrgencyPriority.CRITICAL


@pytest.mark.asyncio
async def test_error_handling_no_extraction():
    """
    Test error handling when extraction is missing from state.
    """
    state: AgentState = {
        "incident_id": "test-123",
        "raw_report": {
            "location": {"type": "Point", "coordinates": [76.0, 10.0]}
        }
    }

    updated_state = await run_risk_decision(state)

    assert "errors" in updated_state
    assert any("No extraction" in err for err in updated_state["errors"])


@pytest.mark.asyncio
async def test_error_handling_no_location():
    """
    Test error handling when location is missing from state.
    """
    state: AgentState = {
        "incident_id": "test-123",
        "extraction": {
            "hazard_type": "FLOOD",
            "people_affected": 5,
            "trapped_count": 5,
            "injured_count": 0,
            "medical_urgencies": [],
            "environmental_hazards": [],
            "extracted_landmark": None,
            "missing_critical_info": [],
            "confidence_score": 0.80,
            "is_ambiguous": False,
            "summary": "Test scenario"
        },
        "raw_report": {}
    }

    updated_state = await run_risk_decision(state)

    assert "errors" in updated_state
    assert any("location" in err.lower() for err in updated_state["errors"])
