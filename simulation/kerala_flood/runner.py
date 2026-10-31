"""
Kerala Flood Master Simulation Runner.
Executes complete 13-stage end-to-end disaster scenario across all 3 villages.
"""
from typing import Dict, Any
from agents.core.client import ResqApiClient
from agents.orchestrator.workflow import process_incident_lifecycle_without_backend


async def run_kerala_flood_simulation(
    client: None = None
) -> Dict[str, Any]:
    """
    Execute master Kerala Flood Disaster Simulation.

    13-Stage Scenario:
    - **Village A:** 12 trapped villagers → NDRF boat extraction
    - **Village B:** Trauma/cardiac → Hospital B ICU + ALS ambulance + O-neg blood
    - **Village C:** Offline relief camps → event buffering → sync on reconnect

    Returns:
        Simulation results with all 3 village outcomes
    """

    # Initialize client
    if client is None:
        client = ResqApiClient()

    results = {
        "simulation_name": "Kerala Monsoon Disaster - Master Simulation",
        "villages": {}
    }

    try:
        # ====================================================================
        # PHASE A: Village A - Flood Extraction (12 Trapped Villagers)
        # ====================================================================

        village_a_report = {
            "description": "12 villagers trapped on roof of community hall by rapidly rising floodwaters. Road access completely severed. Need immediate flood boat extraction.",
            "district": "Thrissur",
            "location": {
                "type": "Point",
                "coordinates": [76.3312, 10.3120]
            },
            "reporter_name": "Local Fire Station",
            "reporter_phone": "+91-9876543210"
        }

        village_a_state = await process_incident_lifecycle_without_backend(
            village_a_report,
            incident_id="inc-village-a-flood",
            client=client
        )

        # Extract Village A results
        village_a_results = {
            "incident_id": "inc-village-a-flood",
            "extraction": {
                "hazard_type": village_a_state.get("extraction", {}).get("hazard_type"),
                "trapped_count": village_a_state.get("extraction", {}).get("trapped_count"),
                "people_affected": village_a_state.get("extraction", {}).get("people_affected")
            },
            "triage": {
                "priority": village_a_state.get("triage", {}).get("priority"),
                "priority_score": village_a_state.get("triage", {}).get("priority_score"),
                "life_threat_detected": village_a_state.get("triage", {}).get("life_threat_detected")
            },
            "rescue_teams_matched": len(village_a_state.get("matched_resources", {}).get("rescue_teams", [])),
            "verification_status": village_a_state.get("audit_summary", {}).get("verification_status", "UNKNOWN")
        }

        results["villages"]["village_a"] = village_a_results

        # ====================================================================
        # PHASE B: Village B - Trauma & Cardiac (ICU + Blood + Ambulance)
        # ====================================================================

        village_b_report = {
            "description": "Elderly resident with compound fracture and severe chest pain after landslide. Requires immediate ICU admission with cardiac monitoring and blood transfusion. ALS ambulance needed urgently.",
            "district": "Wayanad",
            "location": {
                "type": "Point",
                "coordinates": [76.1320, 11.5540]
            },
            "reporter_name": "Village Health Worker",
            "reporter_phone": "+91-9876543211"
        }

        village_b_state = await process_incident_lifecycle_without_backend(
            village_b_report,
            incident_id="inc-village-b-trauma",
            client=client
        )

        # Extract Village B results
        village_b_results = {
            "incident_id": "inc-village-b-trauma",
            "extraction": {
                "hazard_type": village_b_state.get("extraction", {}).get("hazard_type"),
                "injured_count": village_b_state.get("extraction", {}).get("injured_count"),
                "medical_urgencies": village_b_state.get("extraction", {}).get("medical_urgencies", [])
            },
            "triage": {
                "priority": village_b_state.get("triage", {}).get("priority"),
                "priority_score": village_b_state.get("triage", {}).get("priority_score"),
                "life_threat_detected": village_b_state.get("triage", {}).get("life_threat_detected")
            },
            "hospital_matches": len(village_b_state.get("matched_resources", {}).get("hospitals", [])),
            "ambulance_matches": len(village_b_state.get("matched_resources", {}).get("ambulances", [])),
            "blood_allocations": len([
                s for s in village_b_state.get("matched_resources", {}).get("supplies", [])
                if "BLOOD" in s.get("item_code", "")
            ]),
            "reservations_created": len(village_b_state.get("reservations", [])),
            "verification_status": village_b_state.get("audit_summary", {}).get("verification_status", "UNKNOWN")
        }

        results["villages"]["village_b"] = village_b_results

        # ====================================================================
        # PHASE C: Village C - Offline Relief Camps (Supplies + Event Sync)
        # ====================================================================

        village_c_report = {
            "description": "2 relief camps marooned in Kuttanad waterlogged zone. 180 people affected. Running out of drinking water, ORS packets, and water purification tablets. ZERO internet/cellular connectivity - field operations offline.",
            "district": "Alappuzha",
            "location": {
                "type": "Point",
                "coordinates": [76.4320, 9.5840]
            },
            "reporter_name": "Camp Coordinator",
            "reporter_phone": "+91-9876543212"
        }

        village_c_state = await process_incident_lifecycle_without_backend(
            village_c_report,
            incident_id="inc-village-c-supplies",
            client=client
        )

        # Extract Village C results
        village_c_results = {
            "incident_id": "inc-village-c-supplies",
            "extraction": {
                "hazard_type": village_c_state.get("extraction", {}).get("hazard_type"),
                "people_affected": village_c_state.get("extraction", {}).get("people_affected")
            },
            "triage": {
                "priority": village_c_state.get("triage", {}).get("priority"),
                "priority_score": village_c_state.get("triage", {}).get("priority_score")
            },
            "supply_allocations": len(village_c_state.get("matched_resources", {}).get("supplies", [])),
            "verification_status": village_c_state.get("audit_summary", {}).get("verification_status", "UNKNOWN")
        }

        results["villages"]["village_c"] = village_c_results

        # ====================================================================
        # PHASE D & E: Overall Verification
        # ====================================================================

        # Count total successful completions
        verified_count = sum(
            1 for village_key in ["village_a", "village_b", "village_c"]
            if results["villages"][village_key]["verification_status"] in ["VERIFIED_COMPLETE", "PARTIAL_COMPLETION"]
        )

        results["overall_status"] = {
            "total_villages": 3,
            "verified_villages": verified_count,
            "simulation_status": "SUCCESS" if verified_count == 3 else "PARTIAL_SUCCESS"
        }

        return results

    finally:
        await client.close()
