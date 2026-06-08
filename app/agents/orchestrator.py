from app.execution.session import ExecutionSession
from app.execution.state import ExecutionState
from app.events.event_bus import event_bus
from app.events.schema import PrerakEvent
from app.tools.executor import ToolExecutor
from app.models.schemas import PlannerOutput, PlannerStep, CoderOutput
from app.verifier.python_verifier import PythonVerifier
from app.tools.utils import resolve_safe_path
from app.core.config import settings
from app.runtime.runtime_mode import RuntimeMode
from app.agents.planner_agent import PlannerAgent
from app.agents.coder_agent import CoderAgent
from app.context.builder import context_builder
import json

class Orchestrator:
    """The central loop running the deterministic execution pipeline."""
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.executor = ToolExecutor()
        self.verifier = PythonVerifier()
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
    
    async def log_transition(self, session: ExecutionSession, state: ExecutionState):
        session.transition(state)
        await event_bus.publish(PrerakEvent(
            conversation_id=session.convo_id,
            execution_id=session.execution_id,
            event_type="state_transition",
            details={"new_state": state.value}
        ))

    async def run_pipeline(self, convo_id: str, prompt: str) -> bool:
        session = ExecutionSession(workspace_id="test_ws", convo_id=convo_id)
        
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            event_type="execution_started",
            details={"prompt": prompt}
        ))
        
        # 1. PLANNING
        await self.log_transition(session, ExecutionState.PLANNING)
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            event_type="planner_started"
        ))
        
        try:
            # ---> BUILD CONTEXT <---
            context_result = context_builder.build_context(prompt, self.workspace_root)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="context_built",
                details=context_result["metadata"]
            ))
            context_text = context_result["formatted_text"]
            
            if settings.RUNTIME_MODE == RuntimeMode.MOCK.value:
                if "Hello World" in prompt:
                    planner_out = PlannerOutput(
                        goal="Create hello.py",
                        steps=[PlannerStep(step=1, action="write_file", path="hello.py")]
                    )
                elif "Hello PRERAK" in prompt:
                    planner_out = PlannerOutput(
                        goal="Update hello.py",
                        steps=[PlannerStep(step=1, action="edit_file", path="hello.py")]
                    )
                else:
                    raise ValueError("Mock prompt mismatch")
            else:
                planner_out = await self.planner.decompose_task(prompt, context_text)
                
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="planner_completed",
                details=planner_out.model_dump()
            ))
        except Exception as e:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="execution_failed",
                details={"error": f"Planning failed: {str(e)}"}
            ))
            print(f"Planning failed: {e}")
            return False

        # 2. CODING
        await self.log_transition(session, ExecutionState.CODING)
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            event_type="coder_started"
        ))
        step = planner_out.steps[0]
        try:
            if settings.RUNTIME_MODE == RuntimeMode.MOCK.value:
                coder_out = CoderOutput(
                    tool="write_file",
                    path=step.path,
                    content="print('Hello World')"
                )
            else:
                coder_out = await self.coder.handle_task(prompt, step.action, step.path or "", context_text)
                
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="coder_completed",
                details=coder_out.model_dump()
            ))
        except Exception as e:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="execution_failed",
                details={"error": f"Coding failed: {str(e)}"}
            ))
            print(f"Coding failed: {e}")
            return False
        
        # 3. EXECUTING
        await self.log_transition(session, ExecutionState.EXECUTING)
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            event_type="tool_started",
            tool=coder_out.tool,
            path=coder_out.path
        ))
        
        tool_kwargs = {"workspace_root": self.workspace_root, "path": coder_out.path}
        if coder_out.tool == "write_file":
            tool_kwargs["content"] = coder_out.content or ""
        elif coder_out.tool == "edit_file":
            tool_kwargs["old_content"] = coder_out.old_content or ""
            tool_kwargs["new_content"] = coder_out.new_content or ""
            
        result = self.executor.execute(coder_out.tool, tool_kwargs)
        
        await event_bus.publish(PrerakEvent(
            conversation_id=session.convo_id,
            execution_id=session.execution_id,
            event_type="tool_completed",
            tool=coder_out.tool,
            path=coder_out.path,
            success=result.success,
            details={"output": result.output, "error": result.error}
        ))

        if not result.success:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="execution_failed",
                details={"error": f"Tool execution failed: {result.error}"}
            ))
            return False

        # 4. VERIFYING
        await self.log_transition(session, ExecutionState.VERIFYING)
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            event_type="verification_started",
            path=coder_out.path
        ))
        
        target_file = resolve_safe_path(self.workspace_root, coder_out.path)
        is_valid = self.verifier.verify_syntax(str(target_file))
        
        await event_bus.publish(PrerakEvent(
            conversation_id=session.convo_id,
            execution_id=session.execution_id,
            event_type="verification_completed",
            success=is_valid,
            path=coder_out.path
        ))

        if is_valid:
            await self.log_transition(session, ExecutionState.SUCCESS)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="execution_completed"
            ))
            return True
        else:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                event_type="execution_failed",
                details={"error": "Syntax verification failed"}
            ))
            return False
