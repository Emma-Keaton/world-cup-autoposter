"""
Database session management and base model configuration.
Supports both PostgreSQL (with pgvector) and SQLite for development.
Auto-initializes all tables and default settings on startup.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import MetaData
from typing import AsyncGenerator

from app.core.config import settings


# Naming convention for constraints (PostgreSQL-friendly)
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})


class Base(DeclarativeBase):
    """Base class for all models with automatic metadata naming."""
    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (snake_case)."""
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_") + "s"


# Create async engine
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite doesn't support pool_size/max_overflow
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=False,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL with connection pooling
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI routes to get database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables with all models and create default settings.
    
    This function:
    1. Creates all database tables (PostgreSQL or SQLite)
    2. Initializes default settings for web-based configuration
    3. Runs automatically on application startup
    """
    # Import all models to ensure they're registered with Base.metadata
    from app.models import (
        CompetitorAccount,
        ScrapedContent,
        ContentBrief,
        GeneratedVideo,
        AnalyticsRecord,
    )
    # Import new service models
    from app.services.asset_library import AssetModel
    from app.services.batch_processor import BatchJobModel
    from app.core.settings_service import SettingModel
    from app.core.ab_testing import ABTestModel
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize default settings after tables are created
    try:
        from app.core.settings_service import get_settings_service
        settings_service = get_settings_service()
        await settings_service.initialize()
    except Exception as e:
        # Log but don't fail - settings can be created on first access
        from loguru import logger
        logger.debug(f"Settings initialization deferred: {e}")


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()