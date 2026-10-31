"""
Pydantic schemas for authentication and authorization.
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Decoded JWT token payload."""
    user_id: Optional[str] = None


class UserLogin(BaseModel):
    """User login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class UserCreate(BaseModel):
    """User registration/creation schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    phone: str = Field(..., min_length=10, max_length=50, description="Phone number")
    role: str = Field(..., description="User role: SUPERADMIN, CONTROL_ROOM_DISPATCHER, ORG_ADMIN, FIELD_RESPONDER, TRIAGE_DOCTOR")
    organization_id: Optional[UUID] = Field(None, description="Organization ID (nullable for Superadmins)")
    is_active: bool = Field(True, description="Account active status")


class UserResponse(BaseModel):
    """User response schema."""
    id: UUID
    email: str
    full_name: str
    phone: str
    role: str
    organization_id: Optional[UUID]
    is_active: bool

    model_config = {"from_attributes": True}


class UserWithOrganization(UserResponse):
    """User response with organization details."""
    organization_name: Optional[str] = Field(None, description="Organization name")
    organization_type: Optional[str] = Field(None, description="Organization type")


class LoginResponse(BaseModel):
    """Login response with token and user info."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserWithOrganization
