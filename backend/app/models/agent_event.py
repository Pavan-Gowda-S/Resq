"""
AgentEvent model for audit trail of autonomous AI agent reasoning and decisions.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, BigInteger, Integer, ForeignKey, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class AgentEvent(Base):
    """
    Audit trail of autonomous AI agent reasoning, decisions, and API interactions.
    Records agent actions with input context, output decisions, and confidence scores.
    """
    __tablename__ = "agent_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Sequential event ID")

    incident_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Incident FK"
    )

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Agent name (e.g., IncidentIntelligenceAgent)")
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, comment="Action type (e.g., EXTRACTION_COMPLETED, TASK_RECOMMENDED)")

    input_context: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="Input context")
    output_decision: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="Output decision")

    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 3), nullable=True, comment="Confidence score (0.000-1.000)")
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, comment="Execution time in milliseconds")

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="Event timestamp"
    )

    # Relationships
    incident: Mapped[Optional["Incident"]] = relationship("Incident", back_populates="agent_events")

    def __repr__(self) -> str:
        return f"<AgentEvent(id={self.id}, agent='{self.agent_name}', action='{self.action_type}')>"
