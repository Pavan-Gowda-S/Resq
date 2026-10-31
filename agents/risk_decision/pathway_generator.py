"""
Risk & Decision Agent - Multi-Pathway Task Proposal Generator.
Generates linked emergency response tasks based on incident characteristics.
"""
from typing import List
from agents.incident_intelligence.schemas import ExtractedEntities
from agents.risk_decision.schemas import TriageResult, TaskProposal
from shared.constants import TaskType, HazardType, UrgencyPriority
from shared.schemas import GeoPoint


def generate_task_pathways(
    extraction: ExtractedEntities,
    triage: TriageResult,
    coordinates: List[float]
) -> List[TaskProposal]:
    """
    Generate multi-pathway task proposals for incident response.

    Core Principle: One incident can require multiple linked response tasks.
    Example: Trapped injured person needs: rescue → ambulance → hospital bed.

    Args:
        extraction: Structured incident entities
        triage: Triage assessment result
        coordinates: [longitude, latitude] for incident location

    Returns:
        List of proposed emergency response tasks
    """

    proposals = []
    location = GeoPoint(type="Point", coordinates=coordinates)

    # Rule 1: Rescue Extraction Task
    if extraction.trapped_count > 0 or "rising_floodwater" in extraction.environmental_hazards:
        rescue_instructions = f"Rescue extraction required for {extraction.trapped_count} trapped individual(s)"

        if extraction.hazard_type == HazardType.FLOOD:
            rescue_instructions += ". Deploy flood rescue boat team."
        elif extraction.hazard_type == HazardType.LANDSLIDE:
            rescue_instructions += ". Landslide debris clearance needed."
        elif extraction.hazard_type == HazardType.COLLAPSED_STRUCTURE:
            rescue_instructions += ". Structural collapse rescue with specialized equipment."

        if extraction.extracted_landmark:
            rescue_instructions += f" Landmark: {extraction.extracted_landmark}."

        proposals.append(TaskProposal(
            task_type=TaskType.RESCUE_EXTRACTION,
            priority=triage.priority,
            target_location=location,
            instructions=rescue_instructions
        ))

    # Rule 2: Ambulance Transport Task
    needs_ambulance = (
        extraction.injured_count > 0
        or len(extraction.medical_urgencies) > 0
        or triage.life_threat_detected
    )

    if needs_ambulance:
        ambulance_type = "Advanced Life Support (ALS)"

        if any(urgency in extraction.medical_urgencies for urgency in ["cardiac_symptoms", "severe_bleeding", "respiratory_distress"]):
            ambulance_type = "Advanced Life Support (ALS) with paramedic"
        elif extraction.injured_count == 1 and "compound_fracture" in extraction.medical_urgencies:
            ambulance_type = "Basic Life Support (BLS) with immobilization equipment"

        ambulance_instructions = f"{ambulance_type} ambulance required"

        if extraction.medical_urgencies:
            urgencies_str = ", ".join(extraction.medical_urgencies[:3])
            ambulance_instructions += f". Medical conditions: {urgencies_str}"

        if extraction.injured_count > 1:
            ambulance_instructions += f". Total casualties: {extraction.injured_count}."
        else:
            ambulance_instructions += "."

        proposals.append(TaskProposal(
            task_type=TaskType.AMBULANCE_TRANSPORT,
            priority=triage.priority,
            target_location=location,
            instructions=ambulance_instructions
        ))

    # Rule 3: Hospital Admission Task
    needs_hospitalization = (
        triage.priority in [UrgencyPriority.CRITICAL, UrgencyPriority.HIGH]
        and (extraction.injured_count > 0 or len(extraction.medical_urgencies) > 0)
    )

    if needs_hospitalization:
        hospital_instructions = "Hospital admission required"

        if "cardiac_symptoms" in extraction.medical_urgencies:
            hospital_instructions += ". ICU bed with cardiac monitoring needed."
        elif "respiratory_distress" in extraction.medical_urgencies:
            hospital_instructions += ". ICU bed with ventilator support needed."
        elif "compound_fracture" in extraction.medical_urgencies:
            hospital_instructions += ". Emergency bed with orthopedic surgery availability."
        elif "severe_bleeding" in extraction.medical_urgencies:
            hospital_instructions += ". Trauma center with blood transfusion capability."
        else:
            hospital_instructions += ". Emergency bed reservation needed."

        proposals.append(TaskProposal(
            task_type=TaskType.HOSPITAL_ADMISSION,
            priority=triage.priority,
            target_location=location,
            instructions=hospital_instructions
        ))

    # Rule 4: Supply Delivery Task
    needs_supplies = (
        (
            extraction.hazard_type == HazardType.FLOOD
            or any(kw in extraction.summary.lower() for kw in ["camp", "marooned", "water", "supply", "ration", "ors", "antibiotics"])
        )
        and extraction.people_affected >= 20  # Camp or large isolated group
        and extraction.trapped_count == 0  # Not trapped, but isolated
    )

    if needs_supplies:
        supply_instructions = f"Emergency supply delivery for {extraction.people_affected} isolated individuals"

        if "water" in extraction.summary.lower() or "dehydration" in extraction.summary.lower():
            supply_instructions += ". Priority: Drinking water, ORS packets."

        if "medicine" in extraction.summary.lower() or "medical" in extraction.summary.lower():
            supply_instructions += ". Priority: Basic medicines, first-aid kits."

        if "food" in extraction.summary.lower():
            supply_instructions += ". Priority: Food rations."

        proposals.append(TaskProposal(
            task_type=TaskType.SUPPLY_DELIVERY,
            priority=UrgencyPriority.HIGH if triage.priority == UrgencyPriority.CRITICAL else UrgencyPriority.MEDIUM,
            target_location=location,
            instructions=supply_instructions
        ))

    # Rule 5: Relief Camp Shelter (if displaced but not trapped)
    if extraction.people_affected >= 20 and extraction.trapped_count == 0 and not needs_supplies:
        shelter_instructions = f"Relief camp shelter coordination for {extraction.people_affected} displaced individuals."

        proposals.append(TaskProposal(
            task_type=TaskType.RELIEF_CAMP_SHELTER,
            priority=UrgencyPriority.MEDIUM,
            target_location=location,
            instructions=shelter_instructions
        ))

    return proposals
