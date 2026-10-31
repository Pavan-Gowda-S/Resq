"""
StatusEvent model for chronological operational state updates.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class StatusEvent(Base):
    """
    Chronological operational state updates for tasks and incidents.
    Append-only audit trail for status transitions.
    """
    __tablename__ = "status_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Sequential event ID")

    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="Entity type (e.g., INCIDENT, TASK, RESOURCE)")
    entity_id: Mapped[UUID_Type] = mapped_column(UUID(as_uuid=True), nullable=False, comment="Entity UUID")

    previous_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Previous status")
    new_status: Mapped[str] = mapped_column(String(50), nullable=False, comment="New status")

    triggered_by_user_id: Mapped[Optional[UUID_Type]] = mapped_column(UUID(as_uuid=True), nullable=True, comment="User who triggered the transition")

    payload: Mapped[dict] = mapped_column(JSONB, server_default="{}", comment="Additional context")

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="Event timestamp"
    )

    def __repr__(self) -> str:
        return f"<StatusEvent(id={self.id}, entity={self.entity_type}:{self.entity_id}, status={self.previous_status}->{self.new_status})>"
