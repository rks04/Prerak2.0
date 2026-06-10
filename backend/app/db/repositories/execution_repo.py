from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Execution

class ExecutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> Execution:
        obj = Execution(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
        
    async def update_state(self, execution_id: str, state: str, success: bool = None) -> Execution | None:
        result = await self.session.execute(select(Execution).where(Execution.execution_id == execution_id))
        obj = result.scalars().first()
        if obj:
            obj.state = state
            if success is not None:
                obj.success = success
            await self.session.commit()
            await self.session.refresh(obj)
        return obj
