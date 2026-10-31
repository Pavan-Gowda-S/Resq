"""
Automated tests for authentication endpoints.
Tests login, registration, and RBAC protection.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.main import app
from backend.app.models import User
from backend.app.auth.security import get_password_hash


client = TestClient(app)


def test_login_success(db_session, test_user):
    """Test successful login with valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "Test@123456"
        }
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert "user" in data

    # Verify user data
    user_data = data["user"]
    assert user_data["email"] == "test@example.com"
    assert user_data["role"] == "TRIAGE_DOCTOR"
    assert "id" in user_data


def test_login_invalid_credentials():
    """Test login with invalid credentials returns 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_login_wrong_password(test_user):
    """Test login with correct email but wrong password."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "WrongPassword123"
        }
    )

    assert response.status_code == 401


def test_login_inactive_user(db_session, test_organization):
    """Test login with inactive user account returns 403."""
    # Create inactive user
    inactive_user = User(
        email="inactive@example.com",
        password_hash=get_password_hash("Test@123456"),
        full_name="Inactive User",
        phone="+919999999999",
        role="FIELD_RESPONDER",
        organization_id=test_organization.id,
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "Test@123456"
        }
    )

    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


def test_get_current_user_profile(auth_headers):
    """Test getting current authenticated user profile."""
    response = client.get(
        "/api/v1/auth/me",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["role"] == "TRIAGE_DOCTOR"
    assert "organization_name" in data
    assert "organization_type" in data


def test_get_current_user_without_auth():
    """Test accessing profile endpoint without authentication returns 401."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_get_current_user_invalid_token():
    """Test accessing profile with invalid token returns 401."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )

    assert response.status_code == 401


def test_register_user_as_superadmin(superadmin_headers, test_organization):
    """Test user registration by superadmin."""
    response = client.post(
        "/api/v1/auth/register",
        headers=superadmin_headers,
        json={
            "email": "newuser@example.com",
            "password": "NewUser@123",
            "full_name": "New User",
            "phone": "+918888888888",
            "role": "FIELD_RESPONDER",
            "organization_id": str(test_organization.id),
            "is_active": True
        }
    )

    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "newuser@example.com"
    assert data["role"] == "FIELD_RESPONDER"


def test_register_user_duplicate_email(superadmin_headers, test_user):
    """Test registering user with duplicate email returns 400."""
    response = client.post(
        "/api/v1/auth/register",
        headers=superadmin_headers,
        json={
            "email": "test@example.com",  # Already exists
            "password": "Test@123456",
            "full_name": "Duplicate User",
            "phone": "+919999999998",
            "role": "FIELD_RESPONDER",
            "organization_id": None,
            "is_active": True
        }
    )

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_user_without_permission(auth_headers):
    """Test user registration without proper role returns 403."""
    response = client.post(
        "/api/v1/auth/register",
        headers=auth_headers,  # Regular user, not admin
        json={
            "email": "unauthorized@example.com",
            "password": "Test@123456",
            "full_name": "Unauthorized",
            "phone": "+919999999997",
            "role": "FIELD_RESPONDER",
            "organization_id": None,
            "is_active": True
        }
    )

    assert response.status_code == 403


def test_org_admin_register_user_different_org(org_admin_headers, test_organization):
    """Test org admin cannot create users outside their organization."""
    # Create another organization
    from backend.app.models import Organization
    from geoalchemy2.functions import ST_GeogFromText

    # This would need proper setup, simplified for test structure
    response = client.post(
        "/api/v1/auth/register",
        headers=org_admin_headers,
        json={
            "email": "otherorg@example.com",
            "password": "Test@123456",
            "full_name": "Other Org User",
            "phone": "+919999999996",
            "role": "FIELD_RESPONDER",
            "organization_id": "00000000-0000-0000-0000-000000000000",  # Different org
            "is_active": True
        }
    )

    assert response.status_code == 403
