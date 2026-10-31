"""
Test suite for Incident Intelligence Agent.
Validates entity extraction, duplicate detection, and state integration.
"""
import pytest
from agents.core.state import AgentState
from agents.core.client import ResqApiClient
from agents.incident_intelligence.extractor import extract_incident_entities
from agents.incident_intelligence.agent import run_incident_intelligence
from agents.incident_intelligence.schemas import ExtractedEntities
from shared.constants import HazardType
from shared.schemas import GeoPoint


@pytest.mark.asyncio
async def test_village_a_flood_extraction():
    """
    Test 1: Clear Flood Extraction (Village A scenario)
    12 villagers trapped on community hall roof by rapidly rising floodwaters.
    """
    report_text = "12 villagers trapped on roof of community hall by rapidly rising floodwaters in Chalakudy"

    extracted = await extract_incident_entities(report_text, location_hint="Thrissur")

    assert extracted.hazard_type == HazardType.FLOOD
    assert extracted.people_affected == 12
    assert extracted.trapped_count == 12
    assert extracted.injured_count == 0
    assert "rising_floodwater" in extracted.environmental_hazards
    assert extracted.confidence_score > 0.7
    assert not extracted.is_ambiguous


@pytest.mark.asyncio
async def test_village_b_trauma_extraction():
    """
    Test 2: Trauma & Medical Extraction (Village B scenario)
    Elderly resident with compound fracture and severe chest pain.
    """
    report_text = "1 elderly resident with compound fracture and suspected shock near Meppadi. Also complaining of severe chest pain."

    extracted = await extract_incident_entities(report_text, location_hint="Wayanad")

    assert extracted.injured_count >= 1
    assert "compound_fracture" in extracted.medical_urgencies or "fracture" in str(extracted.medical_urgencies)
    assert "cardiac_symptoms" in extracted.medical_urgencies or "shock" in extracted.medical_urgencies
    assert extracted.confidence_score > 0.6


@pytest.mark.asyncio
async def test_multiple_injured_with_trapped():
    """
    Test combined trapped and injured scenario.
    """
    report_text = "4 family members trapped on terrace. One has severe bleeding from leg injury. Water rising fast."

    extracted = await extract_incident_entities(report_text)

    assert extracted.hazard_type == HazardType.FLOOD
    assert extracted.people_affected == 4
    assert extracted.trapped_count == 4
    assert extracted.injured_count >= 1
    assert "severe_bleeding" in extracted.medical_urgencies
    assert "rising_floodwater" in extracted.environmental_hazards


@pytest.mark.asyncio
async def test_ambiguous_report_handling():
    """
    Test 3: Ambiguous Report Handling
    Validates that vague inputs flag low confidence.
    """
    report_text = "help something bad is happening"

    extracted = await extract_incident_entities(report_text)

    assert extracted.is_ambiguous == True
    assert extracted.confidence_score < 0.65
    assert len(extracted.missing_critical_info) > 0


@pytest.mark.asyncio
async def test_landslide_extraction():
    """
    Test landslide hazard detection with local terminology.
    """
    report_text = "Urulpottal happened near Meppadi hills. 3 people injured. Road blocked by debris."

    extracted = await extract_incident_entities(report_text, location_hint="Wayanad")

    assert extracted.hazard_type == HazardType.LANDSLIDE
    assert extracted.injured_count == 3
    assert extracted.people_affected >= 3


@pytest.mark.asyncio
async def test_medical_emergency_extraction():
    """
    Test pure medical emergency (no environmental hazard).
    """
    report_text = "Man having severe chest pain and breathing difficulty. Need ambulance urgently."

    extracted = await extract_incident_entities(report_text)

    assert extracted.hazard_type == HazardType.MEDICAL_EMERGENCY
    assert extracted.injured_count >= 1
    assert "cardiac_symptoms" in extracted.medical_urgencies or "respiratory_distress" in extracted.medical_urgencies


@pytest.mark.asyncio
async def test_landmark_extraction():
    """
    Test landmark and location extraction.
    """
    report_text = "People trapped near Chalakudy Bridge. Floodwater blocking access."

    extracted = await extract_incident_entities(report_text)

    assert extracted.extracted_landmark is not None
    assert "chalakudy" in extracted.extracted_landmark.lower() or "bridge" in extracted.extracted_landmark.lower()


@pytest.mark.asyncio
async def test_duplicate_detection():
    """
    Test 4: Duplicate Detection
    Verifies proximity-based duplicate checking.
    """
    client = ResqApiClient()

    try:
        # Mock backend should return empty list (no duplicates)
        from agents.incident_intelligence.duplicate_detector import check_for_duplicates

        duplicate = await check_for_duplicates(
            client,
            lat=10.3120,
            lng=76.3312,
            radius_m=200
        )

        # In mock mode, no duplicates expected
        assert duplicate is None

    finally:
        await client.close()


@pytest.mark.asyncio
async def test_state_integration():
    """
    Test 5: State Integration
    Validates LangGraph state updates with audit trail.
    """
    # Create initial state
    state: AgentState = {
        "raw_report": {
            "description": "12 villagers trapped on roof by floodwaters in Chalakudy",
            "district": "Thrissur",
            "location": {
                "type": "Point",
                "coordinates": [76.3312, 10.3120]
            }
        }
    }

    # Run intelligence agent
    updated_state = await run_incident_intelligence(state)

    # Verify extraction populated
    assert "extraction" in updated_state
    assert updated_state["extraction"]["hazard_type"] == HazardType.FLOOD.value
    assert updated_state["extraction"]["people_affected"] == 12
    assert updated_state["extraction"]["trapped_count"] == 12

    # Verify audit trail
    assert "audit_trail" in updated_state
    assert len(updated_state["audit_trail"]) > 0

    audit_entry = updated_state["audit_trail"][0]
    assert audit_entry["agent"] == "IncidentIntelligenceAgent"
    assert audit_entry["action"] == "extraction_complete"
    assert "timestamp" in audit_entry
    assert "results" in audit_entry

    # Verify state metadata
    assert "state_updated_at" in updated_state


@pytest.mark.asyncio
async def test_state_without_location():
    """
    Test state processing when location is not provided.
    """
    state: AgentState = {
        "raw_report": {
            "description": "People need help urgently",
            "district": "Ernakulam"
        }
    }

    updated_state = await run_incident_intelligence(state)

    assert "extraction" in updated_state
    assert "duplicate_incidents" not in updated_state  # No location, no duplicate check
    assert "audit_trail" in updated_state


@pytest.mark.asyncio
async def test_error_handling_no_report():
    """
    Test error handling when raw_report is missing from state.
    """
    state: AgentState = {}

    updated_state = await run_incident_intelligence(state)

    assert "errors" in updated_state
    assert len(updated_state["errors"]) > 0
    assert "No raw_report" in updated_state["errors"][0]


@pytest.mark.asyncio
async def test_extraction_schema_validation():
    """
    Test that extracted entities conform to Pydantic schema.
    """
    report_text = "Flood emergency with 5 trapped people"

    extracted = await extract_incident_entities(report_text)

    # Verify it's a valid ExtractedEntities instance
    assert isinstance(extracted, ExtractedEntities)
    assert isinstance(extracted.hazard_type, HazardType)
    assert isinstance(extracted.people_affected, int)
    assert extracted.people_affected >= 1
    assert isinstance(extracted.medical_urgencies, list)
    assert isinstance(extracted.environmental_hazards, list)
    assert 0.0 <= extracted.confidence_score <= 1.0
    assert isinstance(extracted.is_ambiguous, bool)
    assert len(extracted.summary) >= 10


@pytest.mark.asyncio
async def test_confidence_scoring():
    """
    Test confidence score calculation for various report qualities.
    """
    # High quality report
    detailed = await extract_incident_entities(
        "12 people trapped on terrace by rapidly rising floodwater near Chalakudy Bridge. One elderly person with chest pain."
    )
    assert detailed.confidence_score >= 0.7

    # Low quality report
    vague = await extract_incident_entities("help needed")
    assert vague.confidence_score < 0.65
    assert vague.is_ambiguous
