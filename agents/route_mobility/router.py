"""
Route & Mobility Agent - Route Assessment Engine.
Evaluates route safety against known disaster hazards.
"""
import math
from typing import List, Tuple
from agents.route_mobility.schemas import HazardWarning, RouteAssessment


# Known hazard points in Kerala flood scenario
# In production, these would be queried from backend /api/v1/locations/hazards
KNOWN_HAZARDS = [
    {
        "hazard_id": "hazard_aluva_bridge",
        "hazard_type": "FLOODED_ROAD",
        "location_name": "Aluva Periyar Bridge",
        "coordinates": [76.3556, 10.1083],
        "water_depth_cm": 120,
        "status": "ACTIVE"
    },
    {
        "hazard_id": "hazard_chalakudy_road",
        "hazard_type": "FLOODED_ROAD",
        "location_name": "Chalakudy-Kodungallur Road",
        "coordinates": [76.3312, 10.3120],
        "water_depth_cm": 80,
        "status": "ACTIVE"
    }
]


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
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


def point_to_segment_distance(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float
) -> float:
    """
    Calculate minimum distance from point (px, py) to line segment (x1,y1)-(x2,y2).
    Uses simplified planar approximation suitable for short distances.
    """
    # Vector from segment start to point
    dx = px - x1
    dy = py - y1

    # Vector of segment
    sx = x2 - x1
    sy = y2 - y1

    # Segment length squared
    seg_len_sq = sx * sx + sy * sy

    if seg_len_sq == 0:
        # Degenerate segment (point)
        return math.sqrt(dx * dx + dy * dy)

    # Parameter t represents position along segment (0 to 1)
    t = max(0, min(1, (dx * sx + dy * sy) / seg_len_sq))

    # Closest point on segment
    closest_x = x1 + t * sx
    closest_y = y1 + t * sy

    # Distance to closest point
    return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)


def assess_route(
    origin: Tuple[float, float],
    destination: Tuple[float, float]
) -> RouteAssessment:
    """
    Assess route safety and identify hazard restrictions.

    CRITICAL SAFETY: Never claim a route is safe without checking hazards.
    Standard routing APIs don't know about disaster-related obstructions.

    Args:
        origin: (longitude, latitude) origin coordinates
        destination: (longitude, latitude) destination coordinates

    Returns:
        RouteAssessment with safety evaluation and vehicle recommendations
    """

    origin_lng, origin_lat = origin
    dest_lng, dest_lat = destination

    # Calculate straight-line distance (real routing would use road network)
    distance_km = haversine_distance(origin_lat, origin_lng, dest_lat, dest_lng)

    # Estimate travel time (assuming 40 km/h average with disaster conditions)
    estimated_minutes = int((distance_km / 40.0) * 60)

    # Check for hazards along route
    # Simplified: check if any hazard is within 0.5km of the straight line
    hazard_warnings = []
    is_safe = True
    recommended_vehicle = "STANDARD"

    for hazard in KNOWN_HAZARDS:
        hazard_lng, hazard_lat = hazard["coordinates"]

        # Calculate distance from hazard to route line
        distance_to_route = point_to_segment_distance(
            hazard_lng, hazard_lat,
            origin_lng, origin_lat,
            dest_lng, dest_lat
        )

        # Convert to km (rough approximation: 1 degree ≈ 111 km)
        distance_to_route_km = distance_to_route * 111

        # If hazard is within 0.5km of route, it affects travel
        if distance_to_route_km < 0.5:
            warning = HazardWarning(
                hazard_id=hazard["hazard_id"],
                hazard_type=hazard["hazard_type"],
                location_name=hazard["location_name"],
                water_depth_cm=hazard.get("water_depth_cm"),
                status=hazard["status"]
            )
            hazard_warnings.append(warning)

            # Assess safety based on hazard
            if hazard["hazard_type"] == "FLOODED_ROAD":
                water_depth = hazard.get("water_depth_cm", 0)
                if water_depth > 30:
                    is_safe = False
                    if water_depth > 60:
                        recommended_vehicle = "BOAT"
                    else:
                        recommended_vehicle = "4X4"
            elif hazard["hazard_type"] in ["COLLAPSED_BRIDGE", "LANDSLIDE"]:
                is_safe = False
                recommended_vehicle = "HELICOPTER"

    return RouteAssessment(
        origin=[origin_lng, origin_lat],
        destination=[dest_lng, dest_lat],
        distance_km=round(distance_km, 2),
        estimated_minutes=estimated_minutes,
        is_safe=is_safe,
        hazard_warnings=hazard_warnings,
        recommended_vehicle_type=recommended_vehicle
    )
