"""
Audit log middleware for tracking authenticated mutating requests.
"""
import time
import json
from typing import Optional
from uuid import UUID
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.models.audit_log import AuditLog
from backend.app.database.config import AsyncSessionLocal
from backend.app.auth.security import decode_access_token


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Records all authenticated mutating requests (POST, PATCH, PUT, DELETE) to audit_logs.
    Skips: GET requests, /health, /docs, /redoc, /openapi.json, WebSocket upgrades.
    """
    SKIP_PATHS = {"/health", "/", "/docs", "/redoc", "/openapi.json"}
    MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        # Skip non-mutating methods
        if request.method not in self.MUTATING_METHODS:
            return await call_next(request)

        # Skip specific paths
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        # Skip WebSocket upgrades
        if request.headers.get("upgrade") == "websocket":
            return await call_next(request)

        # Extract user_id from JWT token (if present)
        user_id: Optional[UUID] = None
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_access_token(token)
                if payload:
                    user_id_str = payload.get("sub")
                    if user_id_str:
                        user_id = UUID(user_id_str)
            except Exception:
                pass  # Invalid token, proceed without user_id

        # Execute request
        start_time = time.time()
        response = await call_next(request)
        execution_time = time.time() - start_time

        # Record audit log asynchronously (don't block response)
        try:
            await self._record_audit_log(
                user_id=user_id,
                method=request.method,
                path=request.url.path,
                query_params=dict(request.query_params),
                ip_address=request.client.host if request.client else None,
                status_code=response.status_code,
                execution_time=execution_time
            )
        except Exception as e:
            # Never crash the request due to audit logging failure
            print(f"⚠ Audit log failed: {e}")

        return response

    async def _record_audit_log(
        self,
        user_id: Optional[UUID],
        method: str,
        path: str,
        query_params: dict,
        ip_address: Optional[str],
        status_code: int,
        execution_time: float
    ) -> None:
        """Write audit log to database."""
        async with AsyncSessionLocal() as session:
            try:
                action = f"{method} {path}"
                details = {
                    "method": method,
                    "path": path,
                    "query_params": query_params,
                    "status_code": status_code,
                    "execution_time_ms": int(execution_time * 1000)
                }

                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    ip_address=ip_address,
                    request_route=path,
                    details=details
                )

                session.add(audit_log)
                await session.commit()
            except Exception as e:
                await session.rollback()
                print(f"✗ Failed to write audit log: {e}")
            finally:
                await session.close()
