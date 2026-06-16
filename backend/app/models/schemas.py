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

from pydantic import ConfigDict

class CoderOutput(BaseModel):
    tool: str
    
    model_config = ConfigDict(extra='allow')
