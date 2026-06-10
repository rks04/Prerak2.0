from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

class PrerakEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    conversation_id: str
    execution_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str # e.g., planner_started, planner_completed, tool_started, etc.
    workspace_root: Optional[str] = None
    tool: Optional[str] = None
    success: Optional[bool] = None
    path: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
