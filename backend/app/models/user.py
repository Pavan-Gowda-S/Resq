"""
User model representing authorized operators, dispatchers, doctors, and responders.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID as UUID_Type

from sqlalchemy import String, Boolean, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import BaseModel


class User(BaseModel):
    """
    Authorized operators, dispatchers, doctors, and responders affiliated with organizations.
    Roles: SUPERADMIN, CONTROL_ROOM_DISPATCHER, ORG_ADMIN, FIELD_RESPONDER, TRIAGE_DOCTOR
    """
    __tablename__ = "users"

    organization_id: Mapped[Optional[UUID_Type]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        comment="Organization FK (nullable for Superadmins)"
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="User email (unique)")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="Hashed password")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Full name")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, comment="Phone number")

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Role: SUPERADMIN, CONTROL_ROOM_DISPATCHER, ORG_ADMIN, FIELD_RESPONDER, TRIAGE_DOCTOR"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", comment="Account active status")

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="users")
    assigned_tasks: Mapped[list["ResponseTask"]] = relationship("ResponseTask", back_populates="assigned_user", foreign_keys="ResponseTask.assigned_user_id")

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_org_role", "organization_id", "role"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
