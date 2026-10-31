"""
Risk & Decision Agent - Data Schemas.
Validated Pydantic structures for triage assessment and task proposals.
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from shared.constants import UrgencyPriority, TaskType
from shared.schemas import GeoPoint


class TriageResult(BaseModel):
    """
    Deterministic triage assessment result.
    Priority calculations governed by SALT/START-inspired disaster triage rules.
    """

    priority: UrgencyPriority = Field(
        ...,
        description="Incident urgency priority level"
    )

    priority_score: float = Field(
        ...,
        ge=1.0,
        le=10.0,
        description="Numerical priority score (1.0=lowest, 10.0=highest)"
    )

    clinical_rationale: str = Field(
        ...,
        min_length=20,
        description="Clear explanation of clinical and environmental risk factors"
    )

    life_threat_detected: bool = Field(
        default=False,
        description="True if active life-threatening conditions detected"
    )

    requires_human_review: bool = Field(
        default=False,
        description="True if control-room human review required before dispatch"
    )

    missing_info_flags: List[str] = Field(
        default_factory=list,
        description="Critical information gaps that could affect triage accuracy"
    )


class TaskProposal(BaseModel):
    """
    Proposed emergency response task for incident resolution.
    Supports multi-pathway coordination (rescue + medical + supplies).
    """

    task_type: TaskType = Field(
        ...,
        description="Type of emergency response task"
    )

    priority: UrgencyPriority = Field(
        ...,
        description="Task urgency level"
    )

    target_location: GeoPoint = Field(
        ...,
        description="Geographic coordinates for task execution"
    )

    instructions: str = Field(
        ...,
        min_length=10,
        description="Specific instructions for responders"
    )

    parent_task_id: Optional[str] = Field(
        default=None,
        description="ID of parent task if this is a dependent/linked task"
    )


class RiskDecisionOutput(BaseModel):
    """
    Complete risk assessment and task proposal output.
    """

    triage: TriageResult = Field(
        ...,
        description="Triage assessment result"
    )

    proposals: List[TaskProposal] = Field(
        default_factory=list,
        description="Generated task proposals for incident response"
    )
