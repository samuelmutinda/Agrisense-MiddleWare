"""
Drop all tables from the database.

WARNING: This script will permanently delete ALL tables and data in the database!

Usage:
    python scripts/drop_all_tables.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Get project root directory (parent of scripts/)
project_root = Path(__file__).parent.parent

# Add project root to path so we can import app modules
sys.path.insert(0, str(project_root))

# Change to project root directory so .env file is found
os.chdir(project_root)

# Set environment variable to point to .env file location
os.environ.setdefault("ENV_FILE", str(project_root / ".env"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.base import Base

# Import all models so every table is registered in Base.metadata
# (otherwise tables like device_assignment are never dropped and block others)
import app.db.models  # noqa: F401, E402


async def drop_all_tables() -> None:
    """Drop all tables from the database."""
    settings = get_settings()
    
    print("⚠️  WARNING: This will permanently delete ALL tables and data in the database!")
    print(f"Database: {settings.database_url.split('@')[-1] if '@' in settings.database_url else '***'}")
    print("-" * 60)
    
    # Ask for confirmation
    response = input("Are you sure you want to continue? Type 'yes' to confirm: ")
    if response.lower() != "yes":
        print("Aborted. No tables were dropped.")
        return
    
    print("-" * 60)
    print("Dropping all tables...")
    
    # Create database engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with engine.begin() as conn:
            # Drop all tables with CASCADE so dependent objects (FKs, etc.) are removed
            # Use raw SQL so PostgreSQL CASCADE is applied and drop order doesn't block
            for table in reversed(Base.metadata.sorted_tables):
                await conn.execute(text(f'DROP TABLE IF EXISTS "{table.name}" CASCADE'))
        
        print("✅ Successfully dropped all tables!")
        
        # Verify tables are dropped
        async with async_session() as session:
            # Try to query pg_tables to see remaining tables (PostgreSQL specific)
            try:
                result = await session.execute(
                    text("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY tablename
                    """)
                )
                remaining_tables = [row[0] for row in result.all()]
                
                if remaining_tables:
                    print(f"⚠️  Warning: {len(remaining_tables)} tables still exist:")
                    for table in remaining_tables:
                        print(f"   - {table}")
                else:
                    print("✅ Confirmed: No tables remain in the database.")
            except Exception as e:
                # If query fails (might be non-PostgreSQL database), just report success
                print(f"ℹ️  Note: Could not verify table drop status ({e})")
    
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(drop_all_tables())

