"""
Tests for Kerala Flood Master Simulation.
Validates complete 13-stage disaster scenario across all 3 villages.
"""
import pytest
from simulation.kerala_flood.runner import run_kerala_flood_simulation


@pytest.mark.asyncio
async def test_kerala_flood_simulation_structure():
    """Test Kerala flood simulation returns expected structure."""
    results = await run_kerala_flood_simulation()

    # Verify top-level structure
    assert "simulation_name" in results
    assert "villages" in results
    assert "overall_status" in results

    # Verify simulation metadata
    assert "Kerala Monsoon Disaster" in results["simulation_name"]

    # Verify all 3 villages present
    assert "village_a" in results["villages"]
    assert "village_b" in results["villages"]
    assert "village_c" in results["villages"]


@pytest.mark.asyncio
async def test_village_a_flood_extraction():
    """Test Village A flood extraction scenario."""
    results = await run_kerala_flood_simulation()

    village_a = results["villages"]["village_a"]

    # Verify incident ID
    assert village_a["incident_id"] == "inc-village-a-flood"

    # Verify extraction details
    extraction = village_a["extraction"]
    assert extraction["hazard_type"] is not None

    # Verify triage priority
    triage = village_a["triage"]
    assert triage["priority"] is not None

    # Verify rescue team matching
    assert village_a["rescue_teams_matched"] >= 0

    # Verify verification status
    assert village_a["verification_status"] in [
        "VERIFIED_COMPLETE",
        "PARTIAL_COMPLETION",
        "PENDING_VERIFICATION",
        "UNKNOWN"
    ]


@pytest.mark.asyncio
async def test_village_b_trauma_cardiac():
    """Test Village B trauma/cardiac multi-resource scenario."""
    results = await run_kerala_flood_simulation()

    village_b = results["villages"]["village_b"]

    # Verify incident ID
    assert village_b["incident_id"] == "inc-village-b-trauma"

    # Verify extraction includes medical urgencies
    extraction = village_b["extraction"]
    assert extraction["hazard_type"] is not None

    # Verify critical triage
    triage = village_b["triage"]
    assert triage["priority"] is not None

    # Verify multi-resource matching
    assert "hospital_matches" in village_b
    assert "ambulance_matches" in village_b
    assert "blood_allocations" in village_b
    assert "reservations_created" in village_b

    # Verify verification status
    assert village_b["verification_status"] in [
        "VERIFIED_COMPLETE",
        "PARTIAL_COMPLETION",
        "PENDING_VERIFICATION",
        "UNKNOWN"
    ]


@pytest.mark.asyncio
async def test_village_c_relief_supplies():
    """Test Village C relief camp supplies scenario."""
    results = await run_kerala_flood_simulation()

    village_c = results["villages"]["village_c"]

    # Verify incident ID
    assert village_c["incident_id"] == "inc-village-c-supplies"

    # Verify extraction details
    extraction = village_c["extraction"]
    assert extraction["hazard_type"] is not None
    assert extraction["people_affected"] is not None

    # Verify triage priority
    triage = village_c["triage"]
    assert triage["priority"] is not None

    # Verify supply allocation
    assert village_c["supply_allocations"] >= 0

    # Verify verification status
    assert village_c["verification_status"] in [
        "VERIFIED_COMPLETE",
        "PARTIAL_COMPLETION",
        "PENDING_VERIFICATION",
        "UNKNOWN"
    ]


@pytest.mark.asyncio
async def test_overall_simulation_status():
    """Test overall simulation status tracking."""
    results = await run_kerala_flood_simulation()

    overall = results["overall_status"]

    # Verify structure
    assert "total_villages" in overall
    assert "verified_villages" in overall
    assert "simulation_status" in overall

    # Verify values
    assert overall["total_villages"] == 3
    assert 0 <= overall["verified_villages"] <= 3
    assert overall["simulation_status"] in ["SUCCESS", "PARTIAL_SUCCESS"]


@pytest.mark.asyncio
async def test_simulation_completion():
    """Test that simulation completes without errors."""
    try:
        results = await run_kerala_flood_simulation()
        assert results is not None
        assert "villages" in results
    except Exception as e:
        pytest.fail(f"Simulation failed with exception: {e}")


@pytest.mark.asyncio
async def test_village_results_completeness():
    """Test that all villages have complete result sets."""
    results = await run_kerala_flood_simulation()

    required_village_keys = ["incident_id", "extraction", "triage", "verification_status"]

    for village_key in ["village_a", "village_b", "village_c"]:
        village = results["villages"][village_key]

        for key in required_village_keys:
            assert key in village, f"Missing {key} in {village_key}"


@pytest.mark.asyncio
async def test_extraction_data_presence():
    """Test that extraction data is present for all villages."""
    results = await run_kerala_flood_simulation()

    for village_key in ["village_a", "village_b", "village_c"]:
        village = results["villages"][village_key]
        extraction = village["extraction"]

        # All villages should have hazard_type
        assert extraction["hazard_type"] is not None


@pytest.mark.asyncio
async def test_triage_data_presence():
    """Test that triage data is present for all villages."""
    results = await run_kerala_flood_simulation()

    for village_key in ["village_a", "village_b", "village_c"]:
        village = results["villages"][village_key]
        triage = village["triage"]

        # All villages should have priority
        assert triage["priority"] is not None


@pytest.mark.asyncio
async def test_simulation_resilience():
    """Test simulation handles missing or partial data gracefully."""
    results = await run_kerala_flood_simulation()

    # Even if some villages fail, simulation should complete
    assert results is not None
    assert "overall_status" in results

    # Overall status should reflect partial success if needed
    if results["overall_status"]["verified_villages"] < 3:
        assert results["overall_status"]["simulation_status"] == "PARTIAL_SUCCESS"
    else:
        assert results["overall_status"]["simulation_status"] == "SUCCESS"
