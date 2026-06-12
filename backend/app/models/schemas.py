from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PlannerStep(BaseModel):
    step: int
    action: str
    path: Optional[str] = None
    command: Optional[str] = None
    query: Optional[str] = None

class PlannerOutput(BaseModel):
    goal: str
    steps: List[PlannerStep]

class CoderOutput(BaseModel):
    tool: str
    path: Optional[str] = None
    content: Optional[str] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    command: Optional[str] = None
    query: Optional[str] = None
