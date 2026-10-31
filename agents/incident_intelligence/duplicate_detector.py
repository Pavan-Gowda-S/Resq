"""
Incident Intelligence Agent - Duplicate Detector.
Checks for nearby existing incidents to detect duplicate reports.
"""
from typing import Optional, List, Dict, Any
from agents.core.client import ResqApiClient


async def check_for_duplicates(
    client: ResqApiClient,
    lat: float,
    lng: float,
    radius_m: int = 200
) -> Optional[Dict[str, Any]]:
    """
    Check for duplicate incidents within proximity radius.

    Args:
        client: RESQ API client instance
        lat: Latitude of reported incident
        lng: Longitude of reported incident
        radius_m: Search radius in meters (default: 200m)

    Returns:
        Dictionary with duplicate incident details if found, None otherwise.
        Format: {"incident_id": str, "distance_m": float, "incident_number": str}
    """
    duplicates = await client.check_duplicates(lat, lng, radius_m)

    if duplicates and len(duplicates) > 0:
        # Return the closest duplicate
        closest = duplicates[0]
        return {
            "incident_id": closest.get("incident_id"),
            "distance_m": closest.get("distance_m", 0),
            "incident_number": closest.get("incident_number", "UNKNOWN")
        }

    return None
