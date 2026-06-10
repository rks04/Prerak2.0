from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Workspace

class WorkspaceRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> Workspace:
        obj = Workspace(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
        
    async def get_by_id(self, workspace_id: str) -> Workspace | None:
        result = await self.session.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalars().first()
