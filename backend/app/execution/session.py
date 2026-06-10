import uuid
from app.execution.state import ExecutionState

class ExecutionSession:
    """Tracks the state and ID of a single deterministic execution flow."""
    def __init__(self, workspace_id: str, convo_id: str):
        self.execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        self.workspace_id = workspace_id
        self.convo_id = convo_id
        self.state: ExecutionState = ExecutionState.PLANNING

    def transition(self, new_state: ExecutionState):
        self.state = new_state
