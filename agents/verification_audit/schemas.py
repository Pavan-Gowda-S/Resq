"""
Verification & Audit Agent - Data Schemas.
Validated structures for audit summaries and verification results.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AuditSummary(BaseModel):
    """
    Comprehensive audit summary for incident lifecycle verification.
    """

    incident_id: str = Field(
        ...,
        description="Incident identifier"
    )

    total_tasks: int = Field(
        ...,
        ge=0,
        description="Total number of tasks proposed"
    )

    matched_tasks: int = Field(
        ...,
        ge=0,
        description="Number of tasks with resource matches"
    )

    total_reservations: int = Field(
        ...,
        ge=0,
        description="Total number of atomic reservations created"
    )

    has_discrepancies: bool = Field(
        ...,
        description="Whether any discrepancies were detected"
    )

    discrepancy_details: List[str] = Field(
        default_factory=list,
        description="List of discrepancy descriptions"
    )

    verification_status: str = Field(
        ...,
        description="Overall verification status (VERIFIED_COMPLETE, REQUIRES_MANUAL_AUDIT, etc.)"
    )

    timeline: List[dict] = Field(
        default_factory=list,
        description="Execution timeline from audit trail"
    )

    human_review_required: bool = Field(
        default=False,
        description="Whether human review checkpoint was triggered"
    )
