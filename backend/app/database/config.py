"""
Database engine and session configuration.
Supports both async (asyncpg) and sync (psycopg2) connections.
"""
from typing import AsyncGenerator
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import os
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy.pool import NullPool
from backend.app.database.base import Base
# Load environment variables from the project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

# Read database URLs from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://resq_user:resq_password@localhost:5432/resq_db")
DATABASE_SYNC_URL = os.getenv("DATABASE_SYNC_URL", "postgresql://resq_user:resq_password@localhost:5432/resq_db")

# Async engine for FastAPI operations
if os.getenv("TESTING") == "1":
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
else:
    async_engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # Set to True to log all SQL statements
        pool_pre_ping=True,
        pool_size=20,
        max_overflow=10,
    )

# Sync engine for Alembic migrations
sync_engine = create_engine(
    DATABASE_SYNC_URL,
    echo=False,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Sync session factory (for Alembic)
SessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)

# Legacy alias for compatibility
engine = async_engine


async def enable_postgis_extension():
    """
    Ensure PostGIS extension is enabled in the database.
    Should be called on application startup.
    """
    async with async_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get an async database session.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
