from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal, DBState
from fastapi import HTTPException

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for injecting an async database session.
    If the database is unavailable, this cleanly aborts to prevent cascading failures.
    """
    if not DBState.is_connected or AsyncSessionLocal is None:
        raise HTTPException(status_code=503, detail="Database is unavailable")
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
