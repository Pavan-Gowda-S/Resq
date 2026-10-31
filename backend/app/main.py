"""
RESQ Core Application Entrypoint.
Initializes FastAPI gateway, registers middleware, handles exceptions, and mounts routers.
"""
from datetime import datetime
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="RESQ Emergency Coordination Platform API",
    description="Agentic emergency-response and autonomous resource-coordination backend.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the RESQ Emergency Coordination Platform API",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check():
    """
    Standard health check endpoint to verify backend service readiness.
    """
    return HealthResponse(
        status="healthy",
        service="resq-backend",
        version="0.1.0",
        timestamp=datetime.utcnow().isoformat() + "Z"
    )
