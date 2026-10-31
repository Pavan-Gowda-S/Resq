"""
RESQ Agent Configuration Module.
Environment-based configuration using Pydantic Settings.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class AgentConfig(BaseSettings):
    """
    Agent system configuration loaded from environment variables.
    """

    # Gemini AI Configuration
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key (optional in mock mode, required for live LLM calls)"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model identifier"
    )

    # Backend API Configuration
    BACKEND_API_BASE_URL: str = Field(
        default="http://localhost:8000/api/v1",
        description="Base URL for RESQ backend REST API"
    )
    AGENT_SYSTEM_API_KEY: str = Field(
        default="resq_agent_internal_secret_token",
        description="Internal API key for agent-to-backend authentication"
    )

    # Mock Backend Toggle
    USE_MOCK_BACKEND: bool = Field(
        default=True,
        description="Use mock backend service for testing (True) or live backend (False)"
    )

    # HTTP Client Configuration
    REQUEST_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="HTTP request timeout in seconds"
    )
    MAX_RETRIES: int = Field(
        default=3,
        description="Maximum retry attempts for failed requests"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global configuration instance
config = AgentConfig()
