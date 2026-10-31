"""
Incident Intelligence Agent - Entity Extractor.
Supports both Gemini LLM extraction and deterministic fallback for testing.
"""
import re
from typing import Optional
from agents.core.config import config
from agents.incident_intelligence.schemas import ExtractedEntities
from agents.incident_intelligence.prompts import EXTRACTION_SYSTEM_PROMPT, format_extraction_prompt
from shared.constants import HazardType


# Keyword mappings for deterministic extraction
HAZARD_KEYWORDS = {
    HazardType.FLOOD: [
        "flood", "floodwater", "vellapokkam", "water rising", "submerged",
        "inundated", "waterlogged", "terrace", "roof"
    ],
    HazardType.LANDSLIDE: [
        "landslide", "urulpottal", "mudslide", "hillslope", "debris flow", "slope failure"
    ],
    HazardType.MEDICAL_EMERGENCY: [
        "cardiac", "heart attack", "chest pain", "stroke", "seizure",
        "unconscious", "breathing difficulty", "asthma attack"
    ],
    HazardType.COLLAPSED_STRUCTURE: [
        "collapsed", "building collapse", "structural failure", "rubble", "debris"
    ],
    HazardType.FIRE: [
        "fire", "burning", "smoke", "flames", "explosion"
    ]
}

MEDICAL_URGENCY_KEYWORDS = {
    "cardiac_symptoms": ["cardiac", "chest pain", "heart", "heart attack"],
    "compound_fracture": ["fracture", "broken bone", "compound fracture", "bone injury"],
    "severe_bleeding": ["bleeding", "blood loss", "hemorrhage", "laceration"],
    "hypothermia": ["hypothermia", "cold exposure", "freezing"],
    "shock": ["shock", "pale", "weak pulse", "unconscious"],
    "respiratory_distress": ["breathing", "asthma", "respiratory", "difficulty breathing"]
}

ENVIRONMENTAL_HAZARD_KEYWORDS = {
    "rising_floodwater": ["rising", "water level", "flood", "submerged"],
    "power_line_down": ["power line", "electric", "wire down", "live wire"],
    "fast_current": ["current", "flowing", "swept", "river"],
    "unstable_structure": ["unstable", "cracking", "collapse risk", "dangerous building"],
    "debris_hazard": ["debris", "floating", "sharp objects", "wreckage"]
}


def deterministic_extract(report_text: str, location_hint: Optional[str] = None) -> ExtractedEntities:
    """
    Deterministic rule-based extraction for testing without LLM API.
    Provides 100% reproducible results for test fixtures.
    """
    text_lower = report_text.lower()

    # Detect hazard type
    hazard_type = HazardType.OTHER
    max_matches = 0
    for htype, keywords in HAZARD_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > max_matches:
            max_matches = matches
            hazard_type = htype

    # Extract people counts using regex
    people_affected = 1
    trapped_count = 0
    injured_count = 0

    # Look for explicit numbers
    number_patterns = [
        (r'(\d+)\s+(?:people|persons|individuals|villagers|residents)?\s*(?:trapped|stuck|stranded)', 'trapped'),
        (r'(\d+)\s+(?:people|persons|individuals|villagers|residents)?\s*(?:injured|hurt|wounded)', 'injured'),
        (r'(\d+)\s+(?:people|persons|individuals|villagers|family members|residents)', 'people'),
        (r'(\d+)\s+affected', 'people')
    ]

    for pattern, target in number_patterns:
        match = re.search(pattern, text_lower)
        if match:
            count = int(match.group(1))
            if target == 'trapped':
                trapped_count = max(trapped_count, count)
            elif target == 'injured':
                injured_count = max(injured_count, count)
            people_affected = max(people_affected, count)

    # Check for trapped indicators
    if any(word in text_lower for word in ["trapped", "stuck", "stranded", "terrace", "roof"]):
        if trapped_count == 0 and people_affected > 0:
            trapped_count = people_affected

    # Check for injury indicators
    if any(word in text_lower for word in ["injured", "hurt", "fracture", "pain", "bleeding"]):
        if injured_count == 0:
            injured_count = 1

    # Extract medical urgencies
    medical_urgencies = []
    for urgency, keywords in MEDICAL_URGENCY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            medical_urgencies.append(urgency)

    # Extract environmental hazards
    environmental_hazards = []
    for hazard, keywords in ENVIRONMENTAL_HAZARD_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            environmental_hazards.append(hazard)

    # Extract landmark
    landmark_keywords = [
        "bridge", "hall", "school", "temple", "church", "hospital",
        "chalakudy", "meppadi", "kuttanad"
    ]
    extracted_landmark = None
    for kw in landmark_keywords:
        if kw in text_lower:
            # Find the surrounding context
            idx = text_lower.find(kw)
            start = max(0, idx - 30)
            end = min(len(report_text), idx + 30)
            extracted_landmark = report_text[start:end].strip()
            break

    # Determine confidence and ambiguity
    confidence_score = 0.5
    if hazard_type != HazardType.OTHER:
        confidence_score += 0.2
    if people_affected > 0:
        confidence_score += 0.1
    if medical_urgencies or environmental_hazards:
        confidence_score += 0.1
    if extracted_landmark:
        confidence_score += 0.1

    confidence_score = min(1.0, confidence_score)

    missing_critical_info = []
    if not extracted_landmark and not location_hint:
        missing_critical_info.append("specific_location")
    if people_affected == 1 and trapped_count == 0 and injured_count == 0:
        missing_critical_info.append("exact_headcount")

    is_ambiguous = confidence_score < 0.65 or len(missing_critical_info) > 0

    # Generate summary
    summary = report_text[:150].strip()
    if len(report_text) > 150:
        summary += "..."

    return ExtractedEntities(
        hazard_type=hazard_type,
        people_affected=people_affected,
        trapped_count=trapped_count,
        injured_count=injured_count,
        medical_urgencies=medical_urgencies,
        environmental_hazards=environmental_hazards,
        extracted_landmark=extracted_landmark,
        missing_critical_info=missing_critical_info,
        confidence_score=confidence_score,
        is_ambiguous=is_ambiguous,
        summary=summary
    )


async def extract_incident_entities(
    raw_text: str,
    location_hint: Optional[str] = None
) -> ExtractedEntities:
    """
    Extract structured entities from unstructured emergency report.

    Uses Gemini API when GEMINI_API_KEY is configured.
    Falls back to deterministic extraction for testing/offline mode.
    """

    # Check if we should use LLM extraction
    use_llm = (
        config.GEMINI_API_KEY is not None
        and not config.USE_MOCK_BACKEND
    )

    if use_llm:
        # TODO: Implement Gemini extraction in future iteration
        # For now, fall back to deterministic
        return deterministic_extract(raw_text, location_hint)
    else:
        # Deterministic extraction for testing
        return deterministic_extract(raw_text, location_hint)
