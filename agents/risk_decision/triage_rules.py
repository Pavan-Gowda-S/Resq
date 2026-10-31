"""
Risk & Decision Agent - Deterministic Triage Rule Engine.
Implements SALT/START-inspired disaster triage protocols.
"""
from agents.incident_intelligence.schemas import ExtractedEntities
from agents.risk_decision.schemas import TriageResult
from shared.constants import UrgencyPriority, HazardType


# Life-threatening medical urgency indicators
CRITICAL_MEDICAL_KEYWORDS = [
    "cardiac_symptoms",
    "severe_bleeding",
    "respiratory_distress",
    "shock",
    "unconscious"
]

# High-priority medical urgency indicators
HIGH_MEDICAL_KEYWORDS = [
    "compound_fracture",
    "hypothermia"
]


def evaluate_incident_risk(extraction: ExtractedEntities) -> TriageResult:
    """
    Deterministic triage assessment based on SALT/START principles.

    Priority Rules (Non-negotiable):
    - CRITICAL (8.5-10.0): Active life threats
    - HIGH (6.0-8.4): Serious injuries, trapped vulnerable individuals
    - MEDIUM (3.5-5.9): Minor injuries, supply shortages
    - LOW (1.0-3.4): Non-urgent inquiries

    Args:
        extraction: Structured incident entities from Intelligence Agent

    Returns:
        TriageResult with deterministic priority and rationale
    """

    # Determine base score: non-urgent inquiries default to LOW, others to MEDIUM
    if (
        extraction.hazard_type == HazardType.OTHER
        and extraction.trapped_count == 0
        and extraction.injured_count == 0
        and extraction.people_affected < 10
        and not extraction.medical_urgencies
        and not extraction.environmental_hazards
    ):
        score = 2.0  # Base low priority
    else:
        score = 5.0  # Base medium priority

    # Large populations affected elevate priority
    if extraction.people_affected >= 100:
        score = max(score, 7.5)
    elif extraction.people_affected >= 50:
        score = max(score, 6.5)

    life_threat = False
    requires_review = False
    if extraction.trapped_count >= 10 or extraction.people_affected >= 10 or extraction.is_ambiguous:
        requires_review = True
    missing_info = []
    rationale_parts = []

    # Check for critical medical urgencies
    critical_medical = any(
        urgency in extraction.medical_urgencies
        for urgency in CRITICAL_MEDICAL_KEYWORDS
    )

    if critical_medical:
        score = max(score, 9.0)
        life_threat = True
        rationale_parts.append("Critical medical urgency detected (cardiac/respiratory/severe bleeding)")

    # Check for high-priority medical conditions
    high_medical = any(
        urgency in extraction.medical_urgencies
        for urgency in HIGH_MEDICAL_KEYWORDS
    )

    if high_medical:
        score = max(score, 7.5)
        rationale_parts.append("Serious injury detected (fracture/hypothermia)")

    # Evaluate trapped individuals
    if extraction.trapped_count > 0:
        if extraction.trapped_count >= 10:
            score = max(score, 9.5)
            life_threat = True
            rationale_parts.append(f"Mass casualty: {extraction.trapped_count} trapped individuals")
        elif extraction.trapped_count >= 5:
            score = max(score, 8.5)
            life_threat = True
            rationale_parts.append(f"Multiple victims trapped: {extraction.trapped_count} individuals")
        else:
            score = max(score, 7.0)
            rationale_parts.append(f"{extraction.trapped_count} trapped individual(s)")

    # Evaluate environmental hazards
    if "rising_floodwater" in extraction.environmental_hazards:
        if extraction.trapped_count > 0:
            score = max(score, 9.5)
            life_threat = True
            rationale_parts.append("Rapidly rising floodwater threatening trapped individuals")
        else:
            score = max(score, 7.5)
            rationale_parts.append("Rising floodwater hazard")

    if "power_line_down" in extraction.environmental_hazards:
        score = max(score, 8.0)
        rationale_parts.append("Electrocution risk from downed power lines")

    if "fast_current" in extraction.environmental_hazards:
        score = max(score, 8.5)
        life_threat = True
        rationale_parts.append("Dangerous water current")

    # Adjust for hazard type
    if extraction.hazard_type == HazardType.LANDSLIDE:
        score = max(score, 7.5)
        rationale_parts.append("Landslide hazard with debris risk")
    elif extraction.hazard_type == HazardType.FIRE:
        score = max(score, 9.0)
        life_threat = True
        rationale_parts.append("Active fire emergency")
    elif extraction.hazard_type == HazardType.COLLAPSED_STRUCTURE:
        score = max(score, 8.5)
        life_threat = True
        rationale_parts.append("Structural collapse with entrapment risk")

    # Adjust for injury count
    if extraction.injured_count > 0:
        if extraction.injured_count >= 5:
            score = max(score, 8.0)
            rationale_parts.append(f"Multiple casualties: {extraction.injured_count} injured")
        else:
            score = max(score, 6.5)
            rationale_parts.append(f"{extraction.injured_count} injured individual(s)")

    # Check for ambiguous reports
    if extraction.is_ambiguous and extraction.confidence_score < 0.6:
        requires_review = True
        missing_info.extend(extraction.missing_critical_info)
        rationale_parts.append("Ambiguous report requires human verification")
        # Don't downgrade score for ambiguous life threats
        if life_threat:
            rationale_parts.append("Life threat indicators present despite ambiguity")

    # Determine final priority based on score
    if score >= 8.5:
        priority = UrgencyPriority.CRITICAL
    elif score >= 6.0:
        priority = UrgencyPriority.HIGH
    elif score >= 3.5:
        priority = UrgencyPriority.MEDIUM
    else:
        priority = UrgencyPriority.LOW

    # Build clinical rationale
    if not rationale_parts:
        rationale_parts.append("Standard emergency response required")

    clinical_rationale = ". ".join(rationale_parts) + "."

    # Add summary counts
    if extraction.people_affected > 0:
        clinical_rationale = f"{extraction.people_affected} people affected. " + clinical_rationale

    return TriageResult(
        priority=priority,
        priority_score=round(score, 2),
        clinical_rationale=clinical_rationale,
        life_threat_detected=life_threat,
        requires_human_review=requires_review,
        missing_info_flags=missing_info
    )
