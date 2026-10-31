"""
RESQ Interactive Multi-Agent CLI Exploration & Testing Tool.
Allows hands-on testing of custom SOS emergency reports through the complete LangGraph pipeline.
"""
import sys
import asyncio
import json
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Fix Windows console UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agents.core.client import ResqApiClient
from agents.orchestrator.workflow import process_incident_lifecycle_without_backend


async def run_interactive_pipeline(report_text: str, district: str = "Thrissur", coordinates: list = None):
    if coordinates is None:
        coordinates = [76.3312, 10.3120]

    client = ResqApiClient()
    try:
        raw_report = {
            "description": report_text,
            "district": district,
            "location": {
                "type": "Point",
                "coordinates": coordinates
            },
            "reporter_name": "Citizen Explorer",
            "reporter_phone": "+91-9876543210"
        }

        print("\n" + "=" * 70)
        print("🚨 RESQ MULTI-AGENT PIPELINE EXECUTION")
        print("=" * 70)
        print(f"INPUT SOS: \"{report_text}\"")
        print(f"DISTRICT: {district} | COORDINATES: {coordinates}")
        print("=" * 70)

        final_state = await process_incident_lifecycle_without_backend(
            raw_report=raw_report,
            incident_id="interactive-test-001",
            client=client
        )

        # 1. Perception
        ext = final_state.get("extraction", {})
        print("\n[STAGE 1: INCIDENT INTELLIGENCE AGENT]")
        print(f"  • Hazard Type:        {ext.get('hazard_type')}")
        print(f"  • People Affected:    {ext.get('people_affected')}")
        print(f"  • Trapped Count:      {ext.get('trapped_count')}")
        print(f"  • Injured Count:      {ext.get('injured_count')}")
        print(f"  • Medical Urgencies:  {ext.get('medical_urgencies', [])}")
        print(f"  • Hazards:            {ext.get('environmental_hazards', [])}")
        print(f"  • Ambiguity Flag:     {ext.get('is_ambiguous')} (Confidence: {ext.get('confidence_score')})")

        # 2. Triage & Pathways
        triage = final_state.get("triage", {})
        proposals = final_state.get("task_proposals", [])
        print("\n[STAGE 2: RISK & DECISION AGENT]")
        print(f"  • Triage Priority:    {triage.get('priority')} (Score: {triage.get('priority_score')}/10.0)")
        print(f"  • Life Threat:        {triage.get('life_threat_detected')}")
        print(f"  • Clinical Rationale: {triage.get('clinical_rationale')}")
        print(f"  • Human Review Gate:  {triage.get('requires_human_review')}")
        print(f"  • Linked Tasks Generated ({len(proposals)}):")
        for i, p in enumerate(proposals, 1):
            print(f"      {i}. [{p.get('task_type')}] Priority: {p.get('priority')} | \"{p.get('instructions')}\"")

        # 3. Resource Matching
        matched = final_state.get("matched_resources", {})
        print("\n[STAGE 3: AUTONOMOUS MATCHING & MARKETPLACE TIER]")
        if "rescue_teams" in matched and matched["rescue_teams"]:
            for r in matched["rescue_teams"]:
                assigned = r.get("assigned_team", {})
                print(f"  • 🚤 Rescue Team Assigned: {assigned.get('name')} (Capabilities: {assigned.get('capabilities', [])})")
        
        if "hospitals" in matched and matched["hospitals"]:
            for item in matched["hospitals"]:
                h = item.get("hospital", item)
                print(f"  • 🏥 Hospital Matched:     {h.get('hospital_name')} (Bed: {h.get('matched_bed_type')}, Distance: {h.get('distance_km')} km)")

        if "ambulances" in matched and matched["ambulances"]:
            for item in matched["ambulances"]:
                a = item.get("ambulance", item)
                print(f"  • 🚑 Ambulance Dispatched: {a.get('vehicle_plate')} (Type: {a.get('type')})")

        if "supplies" in matched and matched["supplies"]:
            for s in matched["supplies"]:
                print(f"  • 📦 Supply Allocation:   {s.get('item_code')} (Total: {s.get('total_allocated')} units, Approval Required: {s.get('requires_medical_officer_approval')})")

        if "routes" in matched and matched["routes"]:
            for item in matched["routes"]:
                rt = item.get("assessment", item)
                print(f"  • 🗺️ Transit Route:       Safe: {rt.get('is_safe')} | ETA: {rt.get('estimated_minutes')}m | Vehicle: {rt.get('recommended_vehicle_type')}")
                if rt.get("hazard_warnings"):
                    for hw in rt["hazard_warnings"]:
                        print(f"      ⚠️ Hazard Warning: {hw.get('hazard_type')} at {hw.get('location_name')}")

        # 4. Atomic Reservations
        reservations = final_state.get("reservations", [])
        if reservations:
            print("\n[STAGE 4: ATOMIC RESERVATIONS (30-MIN LOCKS)]")
            for res in reservations:
                print(f"  • 🔒 Locked: {res.get('resource_type')} | Org: {res.get('organization_id')} | Reservation ID: {res.get('reservation_id', 'unknown')[:8]}...")

        # 5. Verification & Audit Seal
        audit = final_state.get("audit_summary", {})
        print("\n[STAGE 5: VERIFICATION & AUDIT AGENT]")
        print(f"  • Verification Status: {audit.get('verification_status')}")
        print(f"  • Discrepancies:       {audit.get('has_discrepancies')} ({len(audit.get('discrepancy_details', []))} details)")
        print(f"  • Audit Timeline:      {len(audit.get('timeline', []))} immutable events recorded")
        print("=" * 70 + "\n")

    finally:
        await client.close()


def main():
    if len(sys.argv) > 1:
        custom_text = " ".join(sys.argv[1:])
    else:
        # Default test scenario
        custom_text = (
            "Water levels crossing danger mark in Chalakudy. 4 people trapped on rooftop, "
            "one elderly person having breathing trouble. Bridge is completely submerged."
        )

    asyncio.run(run_interactive_pipeline(custom_text))


if __name__ == "__main__":
    main()
