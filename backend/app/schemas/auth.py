"""
Pydantic schemas for authentication and authorization.
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from backend.app.auth.security import validate_password_complexity


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Decoded JWT token payload."""
    user_id: Optional[str] = None
    role: Optional[str] = None
    organization_id: Optional[str] = None


class UserLogin(BaseModel):
    """User login request schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class RefreshTokenRequest(BaseModel):
    """Token refresh request schema."""
    refresh_token: str = Field(..., description="Valid refresh token")


class UserCreate(BaseModel):
    """User registration/creation schema."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    phone: str = Field(..., min_length=10, max_length=50, description="Phone number")
    role: str = Field(..., description="User role: SUPERADMIN, CONTROL_ROOM_DISPATCHER, ORG_ADMIN, FIELD_RESPONDER, TRIAGE_DOCTOR")
    organization_id: Optional[UUID] = Field(None, description="Organization ID (nullable for Superadmins)")
    is_active: bool = Field(True, description="Account active status")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_complexity(v)
        return v


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
    organization_name: Optional[str] = None
    organization_type: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response schema with access token, refresh token, and user details."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: UserWithOrganization
