from sqlalchemy import Column, String, DateTime
from app.core.database import Base
from datetime import datetime

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), index=True)
    path = Column(String(1024), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
