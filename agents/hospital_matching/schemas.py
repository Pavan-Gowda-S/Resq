"""
Hospital & Medical Matching Agent - Data Schemas.
Validated structures for hospital and ambulance recommendations.
"""
from typing import Optional
from pydantic import BaseModel, Field


class HospitalRecommendation(BaseModel):
    """
    Recommendation for a hospital matched to a patient admission task.
    """

    organization_id: str = Field(
        ...,
        description="Hospital organization identifier"
    )

    hospital_name: str = Field(
        ...,
        description="Hospital display name"
    )

    distance_km: float = Field(
        ...,
        ge=0.0,
        description="Distance from incident location in kilometers"
    )

    available_emergency_beds: int = Field(
        ...,
        ge=0,
        description="Currently available emergency beds"
    )

    available_icu_beds: int = Field(
        ...,
        ge=0,
        description="Currently available ICU beds"
    )

    has_trauma_center: bool = Field(
        default=False,
        description="Whether hospital has trauma center capabilities"
    )

    matched_bed_type: str = Field(
        ...,
        description="Type of bed matched (HOSPITAL_ICU_BED or HOSPITAL_EMERGENCY_BED)"
    )


class AmbulanceRecommendation(BaseModel):
    """
    Recommendation for an ambulance matched to a transport task.
    """

    ambulance_id: str = Field(
        ...,
        description="Ambulance identifier"
    )

    vehicle_plate: str = Field(
        ...,
        description="Vehicle license plate number"
    )

    type: str = Field(
        ...,
        description="Ambulance type (ALS, BLS, NEONATAL, PATIENT_TRANSPORT)"
    )

    distance_km: float = Field(
        ...,
        ge=0.0,
        description="Distance from incident location in kilometers"
    )

    status: str = Field(
        ...,
        description="Ambulance availability status"
    )


class MedicalMatchResult(BaseModel):
    """
    Complete medical matching result including hospital and transport.
    """

    task_id: str = Field(
        ...,
        description="ID of the hospital admission or transport task"
    )

    hospital: Optional[HospitalRecommendation] = Field(
        default=None,
        description="Matched hospital recommendation"
    )

    ambulance: Optional[AmbulanceRecommendation] = Field(
        default=None,
        description="Matched ambulance recommendation"
    )

    reservation_id: Optional[str] = Field(
        default=None,
        description="Bed reservation ID if reservation was created"
    )
