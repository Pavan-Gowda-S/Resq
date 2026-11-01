"""
RESQ Core Application Entrypoint.
Initializes FastAPI gateway, registers security middlewares, handles exceptions, and mounts routers.
"""
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db, enable_postgis_extension
from backend.app.api.v1 import auth, organizations, incidents, tasks, resources, sync
from backend.app.services.pubsub_service import connect_redis, disconnect_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    try:
        await enable_postgis_extension()
        print("[+] PostGIS extension enabled successfully")
    except Exception as e:
        print(f"[-] Failed to enable PostGIS extension: {e}")

    if os.getenv("TESTING") != "1":
        try:
            await connect_redis()
        except Exception as e:
            print(f"[-] Failed to connect to Redis: {e}")

    yield

    if os.getenv("TESTING") != "1":
        try:
            await disconnect_redis()
        except Exception as e:
            print(f"[-] Error during Redis disconnect: {e}")

    print("Shutting down RESQ backend...")


app = FastAPI(
    title="RESQ Emergency Coordination Platform API",
    description="Agentic emergency-response and autonomous resource-coordination backend.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Rate limiter setup
if os.getenv("TESTING") != "1":
    from backend.app.middleware.rate_limiter import limiter
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. Security Headers & Payload Size Middleware (Outermost)
from backend.app.middleware.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# 2. Strict CORS Configuration (Environment-controlled)
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
if os.getenv("ENVIRONMENT") == "development" or os.getenv("TESTING") == "1":
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if allowed_origins != ["*"] else False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# 3. Sanitized Audit Log Middleware
from backend.app.middleware.audit_middleware import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)

# Support frontend /api/public/resq proxy prefix transparently
@app.middleware("http")
async def proxy_prefix_middleware(request: Request, call_next):
    if request.scope.get("path", "").startswith("/api/public/resq"):
        request.scope["path"] = request.scope["path"][len("/api/public/resq"):] or "/"
    return await call_next(request)

# Mount API v1 routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(resources.router)
app.include_router(sync.router, prefix="/api/v1")

# Mount WebSocket router
from backend.app.api.v1 import websockets
app.include_router(websockets.router)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    database: str = "connected"


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to the RESQ Emergency Coordination Platform API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint with active database connectivity check."""
    database_status = "unhealthy"
    try:
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


@app.get("/health/db", tags=["Health"])
async def health_check_db(db: AsyncSession = Depends(get_db)):
    """Health check endpoint that verifies database and PostGIS connectivity."""
    try:
        result = await db.execute(text("SELECT postgis_version();"))
        postgis_ver = result.scalar()
        return {
            "status": "healthy",
            "database": "connected",
            "postgis_version": postgis_ver,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
