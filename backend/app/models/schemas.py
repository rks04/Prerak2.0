from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PlannerOutput(BaseModel):
    goal: str
    task_type: str
    success_criteria: List[str]
    failure_conditions: List[str]
    tool_sequence: List[str]

from pydantic import ConfigDict

class CoderOutput(BaseModel):
    tool: str
    
    model_config = ConfigDict(extra='allow')
