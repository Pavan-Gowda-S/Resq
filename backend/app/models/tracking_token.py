"""
TrackingToken model for citizen incident tracking without authentication.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class TrackingToken(Base):
    """
    Tokens issued to citizens for tracking incident progress without authentication.
    """
    __tablename__ = "tracking_tokens"

    token: Mapped[str] = mapped_column(String(128), primary_key=True, comment="Unique tracking token")

    incident_id: Mapped[UUID_Type] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        comment="Incident FK"
    )

    citizen_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="Citizen phone")

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Token expiration timestamp"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="Token creation timestamp"
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="tracking_tokens")

    def __repr__(self) -> str:
        return f"<TrackingToken(token='{self.token[:16]}...', incident_id={self.incident_id})>"
