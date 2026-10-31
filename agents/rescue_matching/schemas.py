"""
Rescue Matching Agent - Data Schemas.
Validated structures for rescue team recommendations and matching results.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class RescueTeamRecommendation(BaseModel):
    """
    Recommendation for a rescue team matched to an extraction task.
    """

    team_id: str = Field(
        ...,
        description="Unique identifier for the rescue team"
    )

    name: str = Field(
        ...,
        description="Rescue team display name"
    )

    capabilities: List[str] = Field(
        default_factory=list,
        description="Team capabilities (e.g., MOTORIZED_BOAT, FLOOD_EXTRACTION, DIVERS)"
    )

    distance_km: float = Field(
        ...,
        ge=0.0,
        description="Distance from incident location in kilometers"
    )

    status: str = Field(
        ...,
        description="Team availability status (AVAILABLE, DISPATCHED, etc.)"
    )

    suitability_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Match suitability score (0-100, higher is better)"
    )


class RescueMatchResult(BaseModel):
    """
    Complete rescue team matching result for an extraction task.
    """

    task_id: str = Field(
        ...,
        description="ID of the rescue extraction task"
    )

    recommended_teams: List[RescueTeamRecommendation] = Field(
        default_factory=list,
        description="Ranked list of suitable rescue teams"
    )

    assigned_team: Optional[RescueTeamRecommendation] = Field(
        default=None,
        description="Selected team for assignment (best match)"
    )
