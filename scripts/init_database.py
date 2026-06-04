#!/usr/bin/env python3
"""
Database initialization script for Render deployment.
Creates all tables and initializes default settings.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_db


async def main():
    """Initialize database."""
    print("🔧 Initializing database...")
    try:
        await init_db()
        print("✅ Database initialization complete!")
        print("   - All tables created")
        print("   - Default settings initialized")
        return 0
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)