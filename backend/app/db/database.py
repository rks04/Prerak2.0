import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base class for Alembic and SQLAlchemy models
Base = declarative_base()


# Global DB health state
class DBState:
    is_connected = False


# Create async engine
try:
    engine = create_async_engine(
        settings.MYSQL_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    # Async session factory
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

except Exception as e:
    logger.error(f"Failed to initialize database engine: {e}")

    engine = None
    AsyncSessionLocal = None


async def check_db_connection():
    """Check whether database is reachable."""

    if engine is None:
        DBState.is_connected = False
        return False

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        DBState.is_connected = True

        logger.info("Database connection successful.")

        return True

    except Exception as e:
        logger.error(f"Database connection check failed: {e}")

        DBState.is_connected = False

        return False