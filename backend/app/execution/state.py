from enum import Enum

class ExecutionState(str, Enum):
    PLANNING = "PLANNING"
    CODING = "CODING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    RECOVERING = "RECOVERING"
