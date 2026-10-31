"""Check current database state and tables."""
import os
import sys
from sqlalchemy import create_engine, text, inspect

# Read database URL from environment
DATABASE_URL = os.getenv("DATABASE_SYNC_URL", "postgresql://resq_user:resq_password@localhost:5432/resq_db")

try:
    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        # Check if alembic_version table exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'alembic_version'
            );
        """))
        has_alembic_version = result.scalar()

        # Get all tables
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        tables = [row[0] for row in result]

        # Get all indexes
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname;
        """))
        indexes = [row[0] for row in result]

        print("=== Database State ===")
        print(f"\nAlembic version table exists: {has_alembic_version}")

        if has_alembic_version:
            result = conn.execute(text("SELECT version_num FROM alembic_version;"))
            version = result.scalar()
            print(f"Current migration version: {version if version else 'None'}")

        print(f"\nTotal tables: {len(tables)}")
        print("\nTables:")
        for table in tables:
            print(f"  - {table}")

        print(f"\nTotal indexes: {len(indexes)}")
        print("\nIndexes (first 20):")
        for idx in indexes[:20]:
            print(f"  - {idx}")

        if len(indexes) > 20:
            print(f"  ... and {len(indexes) - 20} more")

    print("\n✓ Database connection successful")

except Exception as e:
    print(f"✗ Error: {e}", file=sys.stderr)
    sys.exit(1)
