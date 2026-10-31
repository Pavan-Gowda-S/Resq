"""
WebSocket endpoints for real-time updates.
"""
import json
import asyncio
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.pubsub_service import get_redis
from backend.app.auth.security import decode_access_token

router = APIRouter(tags=["websockets"])


async def authenticate_websocket(token: Optional[str]) -> Optional[dict]:
    """
    Authenticate WebSocket connection using JWT token.

    Args:
        token: JWT token string

    Returns:
        Token payload if valid, None otherwise
    """
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        return payload
    except Exception:
        return None


@router.websocket("/ws/incidents")
async def websocket_incidents(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for live incident feed.

    Auth: Bearer token as query param ?token=<jwt>
    Publishes updates to channel: incidents:*
    """
    # Authenticate
    payload = await authenticate_websocket(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    # Get Redis client
    redis = await get_redis()
    if not redis:
        await websocket.send_json({
            "error": "Redis unavailable",
            "message": "Real-time updates are currently unavailable"
        })
        await websocket.close()
        return

    # Subscribe to incidents pattern
    pubsub = redis.pubsub()
    await pubsub.psubscribe("incidents:*")

    # Keep-alive ping task
    async def send_ping():
        while True:
            try:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    ping_task = asyncio.create_task(send_ping())

    try:
        # Listen for Redis messages and relay to WebSocket
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)

        redis_task = asyncio.create_task(listen_redis())

        # Wait for either disconnect or Redis messages
        await redis_task
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ping_task.cancel()
        await pubsub.punsubscribe("incidents:*")
        await pubsub.close()


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task(
    websocket: WebSocket,
    task_id: UUID,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for live task status feed.

    Auth: Bearer token as query param ?token=<jwt>
    Publishes updates to channel: tasks:{task_id}
    """
    # Authenticate
    payload = await authenticate_websocket(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()

    # Get Redis client
    redis = await get_redis()
    if not redis:
        await websocket.send_json({
            "error": "Redis unavailable",
            "message": "Real-time updates are currently unavailable"
        })
        await websocket.close()
        return

    # Subscribe to specific task channel
    pubsub = redis.pubsub()
    channel = f"tasks:{task_id}"
    await pubsub.subscribe(channel)

    # Keep-alive ping task
    async def send_ping():
        while True:
            try:
                await asyncio.sleep(30)
                await websocket.send_json({"type": "ping"})
            except Exception:
                break

    ping_task = asyncio.create_task(send_ping())

    try:
        # Listen for Redis messages and relay to WebSocket
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)

        redis_task = asyncio.create_task(listen_redis())

        # Wait for either disconnect or Redis messages
        await redis_task
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        ping_task.cancel()
        await pubsub.unsubscribe(channel)
        await pubsub.close()
