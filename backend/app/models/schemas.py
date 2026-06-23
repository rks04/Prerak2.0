from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PlannerOutput(BaseModel):
    goal: str
    success_criteria: List[str]
    failure_conditions: List[str]
    suggested_strategy: List[str]

from pydantic import ConfigDict

class CoderOutput(BaseModel):
    tool: str
    
    model_config = ConfigDict(extra='allow')
