"""
Route & Mobility Agent - Data Schemas.
Validated structures for route assessments and hazard warnings.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class HazardWarning(BaseModel):
    """
    Warning about a specific hazard affecting route safety.
    """

    hazard_id: str = Field(
        ...,
        description="Unique hazard identifier"
    )

    hazard_type: str = Field(
        ...,
        description="Type of hazard (FLOODED_ROAD, COLLAPSED_BRIDGE, LANDSLIDE, etc.)"
    )

    location_name: str = Field(
        ...,
        description="Human-readable location description"
    )

    water_depth_cm: Optional[int] = Field(
        default=None,
        description="Water depth in centimeters (for flood hazards)"
    )

    status: str = Field(
        ...,
        description="Hazard status (ACTIVE, CLEARED, UNDER_ASSESSMENT)"
    )


class RouteAssessment(BaseModel):
    """
    Assessment of route safety and vehicle suitability.
    """

    origin: List[float] = Field(
        ...,
        description="Origin coordinates [longitude, latitude]"
    )

    destination: List[float] = Field(
        ...,
        description="Destination coordinates [longitude, latitude]"
    )

    distance_km: float = Field(
        ...,
        ge=0.0,
        description="Route distance in kilometers"
    )

    estimated_minutes: int = Field(
        ...,
        ge=0,
        description="Estimated travel time in minutes"
    )

    is_safe: bool = Field(
        ...,
        description="Whether route is passable for standard vehicles"
    )

    hazard_warnings: List[HazardWarning] = Field(
        default_factory=list,
        description="List of hazards affecting this route"
    )

    recommended_vehicle_type: str = Field(
        ...,
        description="Recommended vehicle type (STANDARD, 4X4, BOAT, HELICOPTER)"
    )
