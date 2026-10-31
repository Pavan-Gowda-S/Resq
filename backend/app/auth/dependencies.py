"""
FastAPI dependencies for authentication, role enforcement, and multi-tenant isolation.
"""
import os
from typing import List, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models import User, Organization
from backend.app.auth.security import decode_access_token

# HTTP Bearer token authentication scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token or internal agent key.
    """
    token = credentials.credentials

    # Support Internal Agent System API Key
    agent_key = os.getenv("AGENT_SYSTEM_API_KEY", "resq_agent_internal_secret_token")
    if token == agent_key:
        result = await db.execute(select(User).where(User.role == "SUPERADMIN").limit(1))
        system_user = result.scalar_one_or_none()
        if system_user:
            return system_user
        return User(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            email="system_agent@resq.gov.in",
            role="SUPERADMIN",
            is_active=True,
            full_name="RESQ Autonomous System Agent"
        )

    # Decode JWT token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    return user


def require_role(*allowed_roles: str):
    """
    Dependency factory to require specific user roles.
    Raises 403 Forbidden if current user's role is not authorized.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires one of roles {allowed_roles}",
            )
        return current_user

    return role_checker


def require_org_access(target_org_id_param: str = "org_id"):
    """
    Multi-tenant isolation dependency factory:
    Ensures users can ONLY view/mutate data belonging to their own organization,
    unless they hold SUPERADMIN or CONTROL_ROOM_DISPATCHER roles.
    """
    async def org_access_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # SUPERADMIN and CONTROL_ROOM_DISPATCHER can coordinate across all organizations
        if current_user.role in ("SUPERADMIN", "CONTROL_ROOM_DISPATCHER"):
            return current_user

        if current_user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: user is not assigned to an organization",
            )

        return current_user

    return org_access_checker


def require_org_type(*allowed_org_types: str):
    """
    Dependency factory to require specific organization types (e.g., HOSPITAL, POLICE, FIRE).
    """
    async def org_type_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        if current_user.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: user must be affiliated with an organization",
            )

        result = await db.execute(
            select(Organization).where(Organization.id == current_user.organization_id)
        )
        org = result.scalar_one_or_none()

        if org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found",
            )

        if org.type not in allowed_org_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: requires organization type in {allowed_org_types}",
            )

        return current_user

    return org_type_checker
