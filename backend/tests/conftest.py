"""
Pytest fixtures for testing.
Provides test database session, test users, and authentication helpers against PostgreSQL.
"""
import os
os.environ["TESTING"] = "1"
import pytest
from sqlalchemy import text
from geoalchemy2.elements import WKTElement

from backend.app.database.config import SessionLocal, async_engine
from backend.app.models import User, Organization
from backend.app.auth.security import get_password_hash, create_access_token


@pytest.fixture(autouse=True)
def dispose_engine_pool():
    yield
    async_engine.sync_engine.dispose()


@pytest.fixture(scope="function")
def db_session():
    """
    Provide a sync database session connected to PostgreSQL for test fixtures.
    Cleans up temporary test entities upon test completion.
    """
    session = SessionLocal()
    # Clean up test entities beforehand in case of previous test abort (reverse order for FK constraints)
    session.execute(text("DELETE FROM resource_reservations WHERE organization_id IN (SELECT id FROM organizations WHERE registration_number LIKE 'TEST-%' OR registration_number LIKE 'POSTGIS-%');"))
    session.execute(text("DELETE FROM hospital_capacity WHERE organization_id IN (SELECT id FROM organizations WHERE registration_number LIKE 'TEST-%' OR registration_number LIKE 'POSTGIS-%');"))
    session.execute(text("DELETE FROM resource_inventory WHERE organization_id IN (SELECT id FROM organizations WHERE registration_number LIKE 'TEST-%' OR registration_number LIKE 'POSTGIS-%');"))
    session.execute(text("DELETE FROM response_tasks WHERE assigned_user_id IN (SELECT id FROM users WHERE email IN ('test@example.com', 'orgadmin@hospital.org', 'newuser@hospital.org'));"))
    session.execute(text("DELETE FROM users WHERE email IN ('test@example.com', 'orgadmin@hospital.org', 'newuser@hospital.org');"))
    session.execute(text("DELETE FROM organizations WHERE registration_number IN ('TEST-ORG-001', 'TEST-HOSP-001', 'POSTGIS-TEST-001', 'UNAUTH-001');"))
    session.commit()

    try:
        yield session
    finally:
        session.rollback()
        # Clean up in reverse order to respect foreign key constraints
        session.execute(text("DELETE FROM resource_reservations WHERE organization_id IN (SELECT id FROM organizations WHERE registration_number LIKE 'TEST-%' OR registration_number LIKE 'POSTGIS-%');"))
        session.execute(text("DELETE FROM hospital_capacity WHERE organization_id IN (SELECT id FROM organizations WHERE registration_number LIKE 'TEST-%' OR registration_number LIKE 'POSTGIS-%');"))
        session.execute(text("DELETE FROM resource_inventory WHERE organization_id IN (SELECT id FROM organizations WHERE registration_number LIKE 'TEST-%' OR registration_number LIKE 'POSTGIS-%');"))
        session.execute(text("DELETE FROM response_tasks WHERE assigned_user_id IN (SELECT id FROM users WHERE email IN ('test@example.com', 'orgadmin@hospital.org', 'newuser@hospital.org'));"))
        session.execute(text("DELETE FROM users WHERE email IN ('test@example.com', 'orgadmin@hospital.org', 'newuser@hospital.org');"))
        session.execute(text("DELETE FROM organizations WHERE registration_number IN ('TEST-ORG-001', 'TEST-HOSP-001', 'POSTGIS-TEST-001', 'UNAUTH-001');"))
        session.commit()
        session.close()


@pytest.fixture
def test_organization(db_session):
    """Create a test organization."""
    org = Organization(
        name="Test Hospital",
        type="HOSPITAL",
        registration_number="TEST-ORG-001",
        verification_status="VERIFIED",
        contact_email="test@hospital.org",
        contact_phone="+919876543210",
        location=WKTElement("POINT(76.2711 10.8505)", srid=4326),
        address="123 Test Street",
        district="Ernakulam",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def test_user(db_session, test_organization):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("Test@123456"),
        full_name="Test User",
        phone="+919999999999",
        role="TRIAGE_DOCTOR",
        organization_id=test_organization.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_superadmin(db_session):
    """Get or create test superadmin user."""
    user = db_session.query(User).filter_by(email="admin@resq.system").first()
    if not user:
        user = User(
            email="admin@resq.system",
            password_hash=get_password_hash("Admin@123456"),
            full_name="System Administrator",
            phone="+919999999998",
            role="SUPERADMIN",
            organization_id=None,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture
def test_org_admin(db_session, test_organization):
    """Create a test organization admin user."""
    user = User(
        email="orgadmin@hospital.org",
        password_hash=get_password_hash("OrgAdmin@123"),
        full_name="Org Administrator",
        phone="+919999999997",
        role="ORG_ADMIN",
        organization_id=test_organization.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Generate authentication headers for test user."""
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def superadmin_headers(test_superadmin):
    """Generate authentication headers for superadmin user."""
    access_token = create_access_token(data={"sub": str(test_superadmin.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def org_admin_headers(test_org_admin):
    """Generate authentication headers for org admin user."""
    access_token = create_access_token(data={"sub": str(test_org_admin.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def test_task(superadmin_headers):
    """Create a real incident and response task in the database for tests."""
    from backend.app.main import app
    from fastapi.testclient import TestClient
    c = TestClient(app)

    report_res = c.post("/api/v1/incidents/report", json={
        "description": "Emergency incident for reservation testing",
        "location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
        "district": "Ernakulam",
        "people_affected": 2,
    })
    incident_id = report_res.json()["incident_id"]

    task_res = c.post(
        f"/api/v1/incidents/{incident_id}/tasks",
        json={
            "proposals": [{
                "task_type": "HOSPITAL_ADMISSION",
                "priority": "CRITICAL",
                "target_location": {"type": "Point", "coordinates": [76.2711, 10.8505]},
                "instructions": "Admit patient"
            }]
        },
        headers=superadmin_headers
    )
    return task_res.json()["created_tasks"][0]["id"]
