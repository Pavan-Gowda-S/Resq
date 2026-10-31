"""
Authentication API router.
Handles user login, token refresh, logout, registration, and profile endpoints.
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
from backend.app.schemas.auth import RefreshTokenRequest, Token
from backend.app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    revoke_token,
    decode_access_token,
    get_current_user,
)
from backend.app.auth.security import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Conditional rate limiter import
if os.getenv("TESTING") != "1":
    from backend.app.middleware.rate_limiter import limiter
else:
    class MockLimiter:
        def limit(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    limiter = MockLimiter()


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    User login endpoint with rate limiting.
    Authenticates user, returns signed access token (15m) and refresh token (7d).
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Encode user ID, role, and organization_id in token claims
    token_claims = {
        "sub": str(user.id),
        "role": user.role,
        "org_id": str(user.organization_id) if user.organization_id else None
    }

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data=token_claims, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(user_id=str(user.id))

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
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_data
    )


@router.post("/refresh", response_model=Token, status_code=status.HTTP_200_OK)
async def refresh_access_token(
    request_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Exchange a valid refresh token for a fresh access token.
    """
    payload = decode_access_token(request_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    token_claims = {
        "sub": str(user.id),
        "role": user.role,
        "org_id": str(user.organization_id) if user.organization_id else None
    }
    new_access_token = create_access_token(data=token_claims)

    return Token(
        access_token=new_access_token,
        refresh_token=request_data.refresh_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Revoke caller's current Bearer token immediately.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        revoke_token(token)
    return {"message": "Successfully logged out. Token revoked."}


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new user account with RBAC and anti-privilege escalation.
    """
    if current_user.role == "ORG_ADMIN":
        if user_data.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admins can only create users within their own organization"
            )
        # Prevent ORG_ADMIN from creating SUPERADMIN users
        if user_data.role in ("SUPERADMIN", "CONTROL_ROOM_DISPATCHER"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create users with higher administrative privileges"
            )
    elif current_user.role != "SUPERADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPERADMIN or ORG_ADMIN can create new users"
        )

    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

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

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=user_data.role,
        organization_id=user_data.organization_id,
        is_active=user_data.is_active,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.get("/me", response_model=UserWithOrganization)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user profile."""
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
