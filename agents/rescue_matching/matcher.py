"""
Rescue Matching Agent - Team Matcher.
Discovers, filters, and ranks rescue teams for extraction tasks.
"""
import math
from typing import Dict, Any
from agents.core.client import ResqApiClient
from agents.rescue_matching.schemas import RescueTeamRecommendation, RescueMatchResult
from shared.constants import TaskType, HazardType


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.

    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates

    Returns:
        Distance in kilometers
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


async def match_rescue_teams(
    task: Dict[str, Any],
    client: ResqApiClient
) -> RescueMatchResult:
    """
    Match available rescue teams to extraction task.

    Filters by required capabilities and ranks by proximity.

    Args:
        task: Rescue extraction task dictionary
        client: RESQ API client instance

    Returns:
        RescueMatchResult with ranked recommendations and assignment
    """

    task_id = task.get("id", task.get("task_id", "unknown"))
    task_type = task.get("task_type", "")
    target_location = task.get("target_location", {})
    instructions = task.get("instructions", "").lower()

    # Extract incident coordinates
    if "coordinates" in target_location:
        lng, lat = target_location["coordinates"]
    else:
        # Fallback if coordinates missing
        lat, lng = 10.0, 76.0

    # Determine required capabilities based on hazard type and instructions
    required_capabilities = set()

    if "flood" in instructions or "water" in instructions or "boat" in instructions:
        required_capabilities.add("MOTORIZED_BOAT")
        required_capabilities.add("FLOOD_EXTRACTION")

    if "landslide" in instructions or "debris" in instructions:
        required_capabilities.add("DEBRIS_CLEARANCE")

    if "collapse" in instructions or "structural" in instructions:
        required_capabilities.add("STRUCTURAL_RESCUE")
        required_capabilities.add("HEAVY_EQUIPMENT")

    if "dive" in instructions or "submerged" in instructions:
        required_capabilities.add("DIVERS")

    # Query available rescue teams
    teams_response = await client.get_rescue_teams(status="AVAILABLE")
    available_teams = teams_response.get("results", [])

    recommendations = []

    for team in available_teams:
        team_id = team.get("id", "")
        team_name = team.get("name", "Unknown Team")
        team_caps = set(team.get("capabilities", []))
        team_location = team.get("location", {})
        team_status = team.get("status", "AVAILABLE")

        # Calculate distance
        if "coordinates" in team_location:
            team_lng, team_lat = team_location["coordinates"]
            distance = haversine_distance(lat, lng, team_lat, team_lng)
        else:
            distance = 999.0  # Unknown location penalty

        # Calculate capability match score
        if required_capabilities:
            matched_caps = required_capabilities.intersection(team_caps)
            capability_score = (len(matched_caps) / len(required_capabilities)) * 50
        else:
            # No specific requirements, all teams suitable
            capability_score = 50

        # Calculate proximity score (inverse distance, closer = better)
        if distance < 5:
            proximity_score = 50
        elif distance < 15:
            proximity_score = 40
        elif distance < 30:
            proximity_score = 30
        elif distance < 50:
            proximity_score = 20
        else:
            proximity_score = 10

        suitability_score = capability_score + proximity_score

        # Filter: Only include if has required capabilities or no requirements
        if not required_capabilities or matched_caps:
            recommendation = RescueTeamRecommendation(
                team_id=team_id,
                name=team_name,
                capabilities=list(team_caps),
                distance_km=round(distance, 2),
                status=team_status,
                suitability_score=round(suitability_score, 2)
            )
            recommendations.append(recommendation)

    # Sort by suitability score (descending)
    recommendations.sort(key=lambda r: r.suitability_score, reverse=True)

    # Select best team for assignment
    assigned_team = recommendations[0] if recommendations else None

    return RescueMatchResult(
        task_id=task_id,
        recommended_teams=recommendations[:5],  # Top 5
        assigned_team=assigned_team
    )
