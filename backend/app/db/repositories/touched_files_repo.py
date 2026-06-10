from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import TouchedFile

class TouchedFileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> TouchedFile:
        obj = TouchedFile(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
