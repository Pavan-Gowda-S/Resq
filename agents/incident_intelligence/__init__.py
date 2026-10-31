"""
Incident Intelligence Agent Module.
Extracts structured entities from unstructured emergency reports.
"""
from agents.incident_intelligence.agent import run_incident_intelligence
from agents.incident_intelligence.schemas import ExtractedEntities
from agents.incident_intelligence.extractor import extract_incident_entities
from agents.incident_intelligence.duplicate_detector import check_for_duplicates

__all__ = [
    "run_incident_intelligence",
    "ExtractedEntities",
    "extract_incident_entities",
    "check_for_duplicates"
]
