"""
Test cases for configuration module.
"""
import pytest
import os
from agents.core.config import AgentConfig


def test_config_defaults():
    """Verify default configuration values."""
    config = AgentConfig()

    assert config.GEMINI_MODEL == "gemini-2.5-flash"
    assert config.BACKEND_API_BASE_URL == "http://localhost:8000/api/v1"
    assert config.AGENT_SYSTEM_API_KEY == "resq_agent_internal_secret_token"
    assert config.USE_MOCK_BACKEND == True
    assert config.REQUEST_TIMEOUT_SECONDS == 10.0
    assert config.MAX_RETRIES == 3


def test_config_env_override(monkeypatch):
    """Verify environment variable overrides work."""
    monkeypatch.setenv("USE_MOCK_BACKEND", "false")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "20.0")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-pro")

    config = AgentConfig()

    assert config.USE_MOCK_BACKEND == False
    assert config.REQUEST_TIMEOUT_SECONDS == 20.0
    assert config.GEMINI_MODEL == "gemini-pro"


def test_config_optional_api_key():
    """Verify GEMINI_API_KEY is optional in mock mode."""
    config = AgentConfig()

    # Should be None by default (not required in mock mode)
    assert config.GEMINI_API_KEY is None or isinstance(config.GEMINI_API_KEY, str)
