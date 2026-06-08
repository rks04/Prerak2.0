from sqlalchemy import Column, String, DateTime
from app.core.database import Base
from datetime import datetime

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(255), primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Added basic metadata to support the requested memory architecture
    mode = Column(String(50), default="chat") # 'chat' or 'code'
    workspace_id = Column(String(255), nullable=True) 
