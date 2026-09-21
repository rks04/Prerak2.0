from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Any, Optional
from enum import Enum

class StageType(str, Enum):
    EXECUTION = "execution"
    VERIFICATION = "verification"

class StageType(str, Enum):
    EXECUTION = "execution"
    VERIFICATION = "verification"

class VerificationKind(str, Enum):
    COMPILE = "compile"
    LINT = "lint"
    TESTS = "tests"

class TaskType(str, Enum):
    CREATE_PROJECT = "create_project"
    MODIFY_EXISTING = "modify_existing"

class TaskItem(BaseModel):
    task_id: Optional[int] = None
    type: str
    path: Optional[str] = None
    command: Optional[str] = None
    description: Optional[str] = None
    status: str = "pending"
    
    @model_validator(mode="after")
    def validate_task_completeness(self) -> "TaskItem":
        if self.type in ["write_file", "edit_file", "read_file", "delete_file"]:
            if not self.path:
                raise ValueError(f"Task of type '{self.type}' requires a 'path' field.")
        elif self.type == "execute_terminal":
            if not self.command:
                raise ValueError(f"Task of type '{self.type}' requires a 'command' field.")
        return self

class ExecutionStage(BaseModel):
    stage_number: int
    stage_type: StageType = StageType.EXECUTION
    verification_kind: Optional[VerificationKind] = None
    expected_exit_code: Optional[int] = None
    expected_errors: Optional[int] = None
    goal: str
    allowed_tools: List[str]
    completion_condition: str
    success_conditions: List[str] = Field(default_factory=list)
    task_queue: Optional[List[TaskItem]] = Field(default_factory=list)
    
    @model_validator(mode="after")
    def validate_stage_consistency(self) -> "ExecutionStage":
        # Auto-inject read_file if edit_file is allowed
        if "edit_file" in self.allowed_tools and "read_file" not in self.allowed_tools:
            self.allowed_tools.append("read_file")
            
        if not self.allowed_tools:
            raise ValueError("allowed_tools must not be empty.")
            
        if self.stage_type == StageType.EXECUTION:
            # If the stage is meant for doing things other than just creating a project, it must have tasks.
            # create_project is handled purely by the orchestrator so it might have an empty queue.
            if "create_project" not in self.allowed_tools and (self.task_queue is None or len(self.task_queue) == 0):
                raise ValueError("Execution stages must contain at least one actionable task in task_queue (unless only 'create_project' is allowed).")
                
        if self.task_queue:
            used_tools = set()
            for task in self.task_queue:
                if task.type not in self.allowed_tools:
                    raise ValueError(f"Task type '{task.type}' is not in allowed_tools for this stage.")
                used_tools.add(task.type)
                
            expected_tools = set(self.allowed_tools)
            if "read_file" in expected_tools:
                expected_tools.remove("read_file")
            if "create_project" in expected_tools:
                expected_tools.remove("create_project")
                
            missing_tools = expected_tools - used_tools
            if missing_tools:
                raise ValueError(f"The following tools are listed in allowed_tools but have no corresponding task in task_queue: {', '.join(missing_tools)}")
                    
        return self
    
    @model_validator(mode='before')
    @classmethod
    def map_success_criteria(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'success_conditions' not in data and 'success_criteria' in data:
                data['success_conditions'] = data['success_criteria']
        return data

class PlannerOutput(BaseModel):
    goal: str
    task_type: TaskType
    success_criteria: List[str]
    failure_conditions: List[str]
    execution_stages: List[ExecutionStage]

from pydantic import ConfigDict

class CoderOutput(BaseModel):
    tool: str
    
    model_config = ConfigDict(extra='allow')
    
    @model_validator(mode='before')
    @classmethod
    def unpack_nested_args(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If the LLM nested arguments inside 'kwargs' or 'parameters', unpack them
            for key in ['kwargs', 'parameters', 'args']:
                if key in data and isinstance(data[key], dict):
                    nested = data.pop(key)
                    for k, v in nested.items():
                        if k not in data:
                            data[k] = v
        return data
