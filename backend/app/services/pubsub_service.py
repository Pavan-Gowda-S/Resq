"""
Redis Pub/Sub service for real-time updates.
"""
import json
import os
from typing import Optional
import redis.asyncio as aioredis

# Singleton Redis client
redis_client: Optional[aioredis.Redis] = None


async def connect_redis() -> None:
    """Initialize Redis connection."""
    global redis_client

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        redis_client = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        # Test connection
        await redis_client.ping()
        print(f"[+] Redis connected successfully: {redis_url}")
    except Exception as e:
        print(f"[-] Failed to connect to Redis: {e}")
        redis_client = None


async def disconnect_redis() -> None:
    """Close Redis connection."""
    global redis_client

    if redis_client:
        try:
            await redis_client.close()
            print("[+] Redis disconnected")
        except Exception as e:
            print(f"[-] Error disconnecting Redis: {e}")
        finally:
            redis_client = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Return singleton async Redis client."""
    return redis_client


async def publish_incident_update(incident_id: str, payload: dict) -> None:
    """
    Publish incident update to Redis channel.

    Args:
        incident_id: Incident UUID as string
        payload: Update payload dict
    """
    if not redis_client:
        print("⚠ Redis not connected, skipping publish")
        return

    try:
        channel = f"incidents:{incident_id}"
        message = json.dumps(payload)
        await redis_client.publish(channel, message)
    except Exception as e:
        print(f"[-] Failed to publish incident update: {e}")


async def publish_task_update(task_id: str, payload: dict) -> None:
    """
    Publish task update to Redis channel.

    Args:
        task_id: Task UUID as string
        payload: Update payload dict
    """
    if not redis_client:
        print("⚠ Redis not connected, skipping publish")
        return

    try:
        channel = f"tasks:{task_id}"
        message = json.dumps(payload)
        await redis_client.publish(channel, message)
    except Exception as e:
        print(f"[-] Failed to publish task update: {e}")
