"""
Incident service: Incident number generation and token management.
"""
import secrets
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models import Incident, TrackingToken


def generate_incident_number(year: int = None) -> str:
    """
    Generate unique incident number in format: RESQ-YYYY-XXXX

    Args:
        year: Year for the incident number (defaults to current year)

    Returns:
        Formatted incident number string
    """
    if year is None:
        year = datetime.now(timezone.utc).year

    # Generate random 4-digit number (can be enhanced to use sequential numbering)
    random_number = secrets.randbelow(10000)

    return f"RESQ-{year}-{random_number:04d}"


async def generate_unique_incident_number(db: AsyncSession) -> str:
    """
    Generate a unique incident number that doesn't exist in the database.

    Args:
        db: Database session

    Returns:
        Unique incident number string
    """
    max_attempts = 100
    current_year = datetime.now(timezone.utc).year

    for _ in range(max_attempts):
        incident_number = generate_incident_number(current_year)

        # Check if number already exists
        result = await db.execute(
            select(Incident).where(Incident.incident_number == incident_number)
        )
        existing = result.scalar_one_or_none()

        if not existing:
            return incident_number

    # Fallback: use timestamp-based number if random generation fails
    timestamp = int(datetime.now(timezone.utc).timestamp() % 10000)
    return f"RESQ-{current_year}-{timestamp:04d}"


def generate_tracking_token() -> str:
    """
    Generate secure URL-safe tracking token in format: trk_<hex>

    Returns:
        Tracking token string (32 bytes = 64 hex characters + prefix)
    """
    token_hex = secrets.token_hex(32)  # 32 bytes = 64 hex characters
    return f"trk_{token_hex}"


async def create_tracking_token(
    db: AsyncSession,
    incident_id: str,
    citizen_phone: str = None,
    expiration_hours: int = None
) -> TrackingToken:
    """
    Create a tracking token for an incident.

    Args:
        db: Database session
        incident_id: UUID of the incident
        citizen_phone: Optional citizen phone number
        expiration_hours: Token expiration in hours (default from env or 72 hours)

    Returns:
        Created TrackingToken object
    """
    if expiration_hours is None:
        expiration_hours = int(os.getenv("OFFLINE_SYNC_WINDOW_HOURS", "72"))

    token = generate_tracking_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expiration_hours)

    tracking_token = TrackingToken(
        token=token,
        incident_id=incident_id,
        citizen_phone=citizen_phone,
        expires_at=expires_at,
    )

    db.add(tracking_token)
    return tracking_token
