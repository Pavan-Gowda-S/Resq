"""
Authentication API router.
Handles user login, registration, and profile endpoints.
"""
import os
from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.database import get_db
from backend.app.models import User, Organization
from backend.app.schemas import (
    UserLogin,
    UserCreate,
    UserResponse,
    UserWithOrganization,
    LoginResponse,
)
from backend.app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from backend.app.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Conditional rate limiter import
if os.getenv("TESTING") != "1":
    from backend.app.middleware.rate_limiter import limiter
else:
    # Mock limiter for testing
    class MockLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = MockLimiter()


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login endpoint.

    Authenticates user with email and password, returns JWT access token.

    **Contract Reference:** docs/api/api-contracts.md Section 2.1
    """
    # Fetch user by email with organization relationship
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    # Prepare user response with organization details
    user_data = UserWithOrganization(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        organization_id=user.organization_id,
        is_active=user.is_active,
        organization_name=user.organization.name if user.organization else None,
        organization_type=user.organization.type if user.organization else None,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        user=user_data
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    User registration endpoint.

    Creates a new user account. Requires authentication (admin/superadmin only).

    **Authorization:** SUPERADMIN, ORG_ADMIN (can only create users within their org)
    """
    # Check authorization
    if current_user.role == "ORG_ADMIN":
        # Org admins can only create users within their organization
        if user_data.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admins can only create users within their own organization"
            )
    elif current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPERADMIN or ORG_ADMIN can create new users"
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Verify organization exists if provided
    if user_data.organization_id:
        result = await db.execute(
            select(Organization).where(Organization.id == user_data.organization_id)
        )
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

    # Create new user
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
        organization_id=user_data.organization_id,
        is_active=user_data.is_active,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.get("/me", response_model=UserWithOrganization, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user profile.

    Returns user details along with organization information.

    **Authorization:** Any authenticated user
    """
    # Fetch user with organization relationship
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == current_user.id)
    )
    user = result.scalar_one()

    return UserWithOrganization(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        organization_id=user.organization_id,
        is_active=user.is_active,
        organization_name=user.organization.name if user.organization else None,
        organization_type=user.organization.type if user.organization else None,
    )
