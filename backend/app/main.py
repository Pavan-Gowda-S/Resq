"""
RESQ Core Application Entrypoint.
Initializes FastAPI gateway, registers middleware, handles exceptions, and mounts routers.
"""
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, enable_postgis_extension
from backend.app.api.v1 import auth, organizations, incidents, tasks, resources, sync
from backend.app.services.pubsub_service import connect_redis, disconnect_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Executes startup and shutdown logic.
    """
    # Startup: Enable PostGIS extension
    try:
        await enable_postgis_extension()
        print("✓ PostGIS extension enabled successfully")
    except Exception as e:
        print(f"✗ Failed to enable PostGIS extension: {e}")

    # Startup: Connect to Redis (skip in testing)
    if os.getenv("TESTING") != "1":
        try:
            await connect_redis()
        except Exception as e:
            print(f"✗ Failed to connect to Redis: {e}")

    yield

    # Shutdown: Disconnect Redis
    if os.getenv("TESTING") != "1":
        try:
            await disconnect_redis()
        except Exception as e:
            print(f"✗ Error during Redis disconnect: {e}")

    print("Shutting down RESQ backend...")


app = FastAPI(
    title="RESQ Emergency Coordination Platform API",
    description="Agentic emergency-response and autonomous resource-coordination backend.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Rate limiter setup (skip in testing)
if os.getenv("TESTING") != "1":
    from backend.app.middleware.rate_limiter import limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Audit log middleware (after CORS)
from backend.app.middleware.audit_middleware import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)

# Mount API v1 routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(resources.router)
app.include_router(sync.router, prefix="/api/v1")

# Mount WebSocket router (no /api/v1 prefix)
from backend.app.api.v1 import websockets
app.include_router(websockets.router)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    database: str


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the RESQ Emergency Coordination Platform API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Enhanced health check endpoint to verify backend service and database readiness.
    Performs an active database connection check.
    """
    database_status = "unhealthy"

    try:
        # Execute a simple query to verify database connectivity
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"

    overall_status = "healthy" if database_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        service="resq-backend",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=database_status
    )
