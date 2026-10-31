import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["health"] == "/health"
    assert data["docs"] == "/docs"

def test_health_check_endpoint():
    """Test the enhanced health check endpoint with database connectivity."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data
    assert "database" in data

    # Verify expected values
    assert data["service"] == "resq-backend"
    assert data["version"] == "0.1.0"

    # Status should be "healthy" if database is connected, or "degraded" otherwise
    assert data["status"] in ["healthy", "degraded"]

    # Database field should indicate connection status
    # Will be "connected" if database is available, or an error message otherwise
    if data["status"] == "healthy":
        assert data["database"] == "connected"

    # Timestamp should be a valid ISO 8601 string
    assert "T" in data["timestamp"]
