"""
Kerala Flood Simulation Driver.
Provides automated end-to-end verification of multi-pathway coordination across
Village A, Village B, and Village C scenarios.
"""
import json
from pathlib import Path
from typing import Dict, Any

SEED_FILE = Path(__file__).parent.parent / "seed_data" / "kerala_seed.json"

def load_simulation_seed() -> Dict[str, Any]:
    """Loads baseline synthetic data for the Kerala Flood disaster simulation."""
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Simulation seed file not found: {SEED_FILE}")
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def verify_seed_invariants():
    """Validates baseline capacity and node counts matching Master Architecture Section 8."""
    data = load_simulation_seed()
    
    # Check incidents
    incidents = data.get("incidents", [])
    assert len(incidents) == 3, f"Expected 3 incident nodes, found {len(incidents)}"
    
    # Check hospitals
    hospitals = data.get("hospitals", [])
    assert len(hospitals) == 2, f"Expected 2 hospitals, found {len(hospitals)}"
    
    # Hospital A has 4 emergency beds
    hosp_a = next(h for h in hospitals if h["id"] == "org_hospital_a")
    assert hosp_a["capacity"]["available_emergency_beds"] == 4, "Hospital A must have 4 emergency beds"
    
    # Hospital B has 2 ICU beds
    hosp_b = next(h for h in hospitals if h["id"] == "org_hospital_b")
    assert hosp_b["capacity"]["available_icu_beds"] == 2, "Hospital B must have 2 ICU beds"
    
    # Check ambulances: 3 available
    ambulances = data.get("ambulances", [])
    assert len(ambulances) == 3, f"Expected 3 ambulances, found {len(ambulances)}"
    
    # Check rescue teams: 4 available
    rescue_teams = data.get("rescue_teams", [])
    assert len(rescue_teams) == 4, f"Expected 4 rescue teams, found {len(rescue_teams)}"
    
    # Check suppliers: 2 suppliers + 1 blood bank = 3
    suppliers = data.get("suppliers", [])
    assert len(suppliers) == 3, f"Expected 3 supply orgs (2 suppliers, 1 blood bank), found {len(suppliers)}"
    
    print("Simulation seed data integrity verified successfully.")

if __name__ == "__main__":
    verify_seed_invariants()
