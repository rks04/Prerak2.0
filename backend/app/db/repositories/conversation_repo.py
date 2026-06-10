from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import Conversation

class ConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
        
    async def create(self, **kwargs) -> Conversation:
        obj = Conversation(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj
        
    async def get_by_id(self, conversation_id: str) -> Conversation | None:
        result = await self.session.execute(select(Conversation).where(Conversation.id == conversation_id))
        return result.scalars().first()
