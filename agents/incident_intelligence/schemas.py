"""
Incident Intelligence Agent - Extraction Data Schemas.
Validated Pydantic structures for entity extraction from unstructured reports.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from shared.constants import HazardType


class ExtractedEntities(BaseModel):
    """
    Structured extraction result from an unstructured emergency report.
    Designed to normalize chaotic citizen descriptions into actionable data.
    """

    hazard_type: HazardType = Field(
        ...,
        description="Primary hazard category extracted from report"
    )

    people_affected: int = Field(
        default=1,
        ge=1,
        description="Total number of people affected/requiring assistance"
    )

    trapped_count: int = Field(
        default=0,
        ge=0,
        description="Number of people physically trapped/unable to self-evacuate"
    )

    injured_count: int = Field(
        default=0,
        ge=0,
        description="Number of people with reported injuries or medical conditions"
    )

    medical_urgencies: List[str] = Field(
        default_factory=list,
        description="Detected medical conditions (e.g., cardiac_symptoms, fracture, bleeding)"
    )

    environmental_hazards: List[str] = Field(
        default_factory=list,
        description="Environmental dangers detected (e.g., rising_water, power_lines, debris)"
    )

    extracted_landmark: Optional[str] = Field(
        default=None,
        description="Notable landmark or location identifier from report"
    )

    missing_critical_info: List[str] = Field(
        default_factory=list,
        description="Critical information gaps identified (e.g., exact_headcount, location)"
    )

    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score (0.0 to 1.0)"
    )

    is_ambiguous: bool = Field(
        default=False,
        description="True if confidence < 0.65 or key information missing"
    )

    summary: str = Field(
        ...,
        min_length=10,
        description="Concise normalized summary of the incident"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "hazard_type": "FLOOD",
                "people_affected": 12,
                "trapped_count": 12,
                "injured_count": 0,
                "medical_urgencies": [],
                "environmental_hazards": ["rising_floodwater", "submerged_access_road"],
                "extracted_landmark": "Community hall near Chalakudy Bridge",
                "missing_critical_info": [],
                "confidence_score": 0.92,
                "is_ambiguous": False,
                "summary": "12 villagers trapped on community hall roof by rapidly rising floodwaters"
            }
        }
