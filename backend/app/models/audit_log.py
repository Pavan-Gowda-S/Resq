"""
AuditLog model for immutable compliance and security record.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, BigInteger, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


class AuditLog(Base):
    """
    Immutable compliance and security record of all authenticated mutations.
    Append-only ledger for audit trails and compliance.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="Sequential audit log ID")

    user_id: Mapped[Optional[UUID_Type]] = mapped_column(UUID(as_uuid=True), nullable=True, comment="User UUID (nullable for system actions)")

    action: Mapped[str] = mapped_column(String(100), nullable=False, comment="Action performed")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, comment="IP address")
    request_route: Mapped[str] = mapped_column(String(255), nullable=False, comment="Request route/endpoint")

    details: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="Action details")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
        comment="Audit timestamp"
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', user={self.user_id})>"
