from app.execution.session import ExecutionSession
from app.execution.state import ExecutionState
from app.events.event_bus import event_bus
from app.events.schema import PrerakEvent
from app.tools.executor import ToolExecutor
from app.models.schemas import PlannerOutput, CoderOutput
from app.verifier.python_verifier import PythonVerifier
from app.tools.utils import resolve_safe_path
from app.core.config import settings
from app.runtime.runtime_mode import RuntimeMode
from app.agents.planner_agent import PlannerAgent
from app.agents.coder_agent import CoderAgent
from app.context.builder import context_builder
from app.db.database import AsyncSessionLocal
from app.workspace.manager import WorkspaceManager
from pathlib import Path
import json

class Orchestrator:
    """The central loop running the deterministic execution pipeline."""
    def __init__(self, workspace_root: str, workspace_id: str):
        self.workspace_root = workspace_root
        self.workspace_id = workspace_id
        self.executor = ToolExecutor()
        self.verifier = PythonVerifier()
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
    
    async def log_transition(self, session: ExecutionSession, state: ExecutionState):
        session.transition(state)
        await event_bus.publish(PrerakEvent(
            conversation_id=session.convo_id,
            execution_id=session.execution_id,
            workspace_root=self.workspace_root,
            event_type="state_transition",
            details={"new_state": state.value}
        ))

    async def run_pipeline(self, convo_id: str, prompt: str) -> bool:
        session = ExecutionSession(workspace_id=self.workspace_id, convo_id=convo_id)
        touched_files = []
        recent_touched_paths = []
        final_success = False
        
        if AsyncSessionLocal is not None:
            try:
                async with AsyncSessionLocal() as db_session:
                    manager = WorkspaceManager(db_session)
                    recent_touched_paths = await manager.get_recent_touched_files(self.workspace_id)
            except Exception as e:
                print(f"Failed to load recent touched files from DB: {e}")
        
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            workspace_root=self.workspace_root,
            event_type="execution_started",
            details={"prompt": prompt}
        ))
        
        # 1. PLANNING
        await self.log_transition(session, ExecutionState.PLANNING)
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            workspace_root=self.workspace_root,
            event_type="planner_started"
        ))
        
        try:
            # ---> BUILD PLANNER CONTEXT <---
            context_result = context_builder.build_planner_context(prompt, self.workspace_root, convo_id)
            context_text = context_result["formatted_text"]
            
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="context_built",
                details=context_result["metadata"]
            ))
            
            if settings.RUNTIME_MODE == RuntimeMode.MOCK.value:
                planner_out = PlannerOutput(
                    goal="Create mock task",
                    success_criteria=["Task completed"]
                )
            else:
                planner_out = await self.planner.decompose_task(f"Task: {prompt}\n\nWorkspace Context:\n{context_text}")
                
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="planner_completed",
                details=planner_out.model_dump()
            ))
            
        except Exception as e:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="execution_failed",
                details={"error": f"Planning failed: {str(e)}"}
            ))
            print(f"Planning failed: {e}")
            return False

        # 2. AUTONOMOUS REACT LOOP
        await self.log_transition(session, ExecutionState.CODING)
        conversation_history = []
        task_description = f"Goal: {planner_out.goal}\nSuccess Criteria:\n" + "\n".join(f"- {c}" for c in planner_out.success_criteria)
        
        MAX_ITERATIONS = 15
        step_success = False
        failure_memory = {}
        
        for iteration in range(MAX_ITERATIONS):
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="coder_started",
                details={"iteration": iteration + 1}
            ))
            
            try:
                # ---> BUILD CODER CONTEXT <---
                coder_context_result = context_builder.build_coder_context(prompt, self.workspace_root, "")
                coder_context_text = coder_context_result["formatted_text"]
                
                coder_out = await self.coder.handle_task(task_description, conversation_history, coder_context_text)
                
                await event_bus.publish(PrerakEvent(
                    conversation_id=convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
                    event_type="coder_completed",
                    details=coder_out.model_dump()
                ))
            except Exception as e:
                await self.log_transition(session, ExecutionState.FAILED)
                await event_bus.publish(PrerakEvent(
                    conversation_id=convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
                    event_type="execution_failed",
                    details={"error": f"Coding failed: {str(e)}"}
                ))
                return False

            # Check for task completion
            if coder_out.tool == "task_completed":
                step_success = True
                break
                
            # 3. EXECUTING
            await self.log_transition(session, ExecutionState.EXECUTING)
            
            # --- DYNAMIC TOOL DISPATCH ---
            tool_kwargs = coder_out.model_extra.copy() if coder_out.model_extra else {}
            tool_kwargs["workspace_root"] = self.workspace_root
            
            # Record what tool was called to history
            safe_log_kwargs = {k: v for k, v in tool_kwargs.items() if k != "workspace_root"}
            conversation_history.append({
                "role": "assistant",
                "content": json.dumps({"tool": coder_out.tool, **safe_log_kwargs})
            })
            
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="tool_started",
                tool=coder_out.tool,
                details=safe_log_kwargs
            ))
            
            # Record Execution Memory (Phase 13D.5)
            # In a full implementation, we would insert this into the DB.
            # For now, it's tracked in conversation_history array which is attached to the state memory below.
            
            result = self.executor.execute(coder_out.tool, tool_kwargs)
            
            # Append result to history
            if result.success:
                conversation_history.append({"role": "system", "content": f"Success: {result.output}"})
            else:
                import hashlib
                error_hash = hashlib.md5(str(result.error).encode()).hexdigest()
                failure_memory[error_hash] = failure_memory.get(error_hash, 0) + 1
                
                if failure_memory[error_hash] >= 3:
                    conversation_history.append({
                        "role": "system", 
                        "content": f"Error: {result.error}\n\n[SYSTEM WARNING]: You have hit this EXACT SAME ERROR {failure_memory[error_hash]} times in a row. Stop repeating the same failed strategy. You MUST try a completely different approach (e.g. read the file to understand it, use a different tool, or search for a different solution)."
                    })
                else:
                    conversation_history.append({"role": "system", "content": f"Error: {result.error}"})
                    
                await self.log_transition(session, ExecutionState.RECOVERING)
                
            await event_bus.publish(PrerakEvent(
                conversation_id=session.convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="tool_completed",
                tool=coder_out.tool,
                success=result.success,
                details={"output": result.output, "error": result.error}
            ))

        if not step_success:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="execution_failed",
                details={"error": "Max iterations reached without task_completed"}
            ))
            await self._save_state(session.execution_id, convo_id, prompt, ExecutionState.FAILED.value, False, touched_files)
            return False

        # 4. COMPLETION
        await self.log_transition(session, ExecutionState.SUCCESS)
        
        final_summary = "Task completed successfully."
        try:
            from app.agents.synthesizer_agent import SynthesizerAgent
            synthesizer = SynthesizerAgent()
            final_summary = await synthesizer.synthesize(task_description, conversation_history)
        except Exception as e:
            print(f"Synthesizer error: {e}")
            
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            workspace_root=self.workspace_root,
            event_type="execution_completed",
            details={"summary": final_summary}
        ))
        
        # --- Phase 13D.5: Execution Memory ---
        try:
            exec_dir = Path(self.workspace_root) / ".memory" / "executions"
            exec_dir.mkdir(parents=True, exist_ok=True)
            log_file = exec_dir / f"{session.execution_id}.json"
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(conversation_history, f, indent=2)
        except Exception as e:
            print(f"Failed to write execution memory: {e}")
            
        await self._save_state(session.execution_id, convo_id, prompt, ExecutionState.SUCCESS.value, True, touched_files)
        return True

    async def _save_state(self, exec_id, convo_id, prompt, state, success, touched_files):
        if AsyncSessionLocal is None:
            return
        try:
            async with AsyncSessionLocal() as db_session:
                manager = WorkspaceManager(db_session)
                await manager.save_execution_state(
                    self.workspace_id,
                    convo_id,
                    exec_id,
                    prompt,
                    state,
                    success,
                    touched_files
                )
        except Exception as e:
            print(f"Failed to save execution state to DB: {e}")
