from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.database import Base
import uuid

def generate_uuid():
    return uuid.uuid4().hex

class Workspace(Base):
    __tablename__ = "workspaces"
    
    id = Column(String(32), primary_key=True, default=generate_uuid)
    workspace_path = Column(String(500), nullable=False)
    summary_path = Column(String(500), nullable=True)
    last_opened = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String(32), primary_key=True, default=generate_uuid)
    type = Column(String(50), nullable=False, default="chat")
    title = Column(String(255), nullable=False, default="New Conversation")
    workspace_id = Column(String(32), ForeignKey("workspaces.id"), nullable=True)
    json_path = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Execution(Base):
    __tablename__ = "executions"
    
    execution_id = Column(String(32), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False)
    state = Column(String(50), nullable=False)
    success = Column(Boolean, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

class TouchedFile(Base):
    __tablename__ = "touched_files"
    
    id = Column(String(32), primary_key=True, default=generate_uuid)
    execution_id = Column(String(32), ForeignKey("executions.execution_id"), nullable=False)
    workspace_id = Column(String(32), ForeignKey("workspaces.id"), nullable=True)
    file_path = Column(String(500), nullable=False)
    action = Column(String(50), nullable=False) # e.g. edit, write, delete
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
