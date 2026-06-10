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
from app.db.database import AsyncSessionLocal
from app.workspace.manager import WorkspaceManager
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

        # 2. CODING & EXECUTING LOOP
        MAX_RETRIES = 3
        for step in planner_out.steps:
            step_success = False
            error_feedback = None
            
            for attempt in range(MAX_RETRIES):
                await self.log_transition(session, ExecutionState.CODING)
                await event_bus.publish(PrerakEvent(
                    conversation_id=convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
                    event_type="coder_started"
                ))
                
                try:
                    # ---> BUILD CODER CONTEXT FOR THIS SPECIFIC STEP <---
                    coder_context_result = context_builder.build_coder_context(prompt, self.workspace_root, step.path or "")
                    coder_context_text = coder_context_result["formatted_text"]
                    
                    if settings.RUNTIME_MODE == RuntimeMode.MOCK.value:
                        coder_out = CoderOutput(
                            tool="write_file",
                            path=step.path,
                            content="print('Hello World')"
                        )
                    else:
                        coder_out = await self.coder.handle_task(prompt, step.action, step.path or "", coder_context_text, error_feedback)
                        
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
                    print(f"Coding failed: {e}")
                    return False
                
                # 3. EXECUTING
                await self.log_transition(session, ExecutionState.EXECUTING)
                await event_bus.publish(PrerakEvent(
                    conversation_id=convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
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
                elif coder_out.tool == "execute_terminal":
                    tool_kwargs = {"workspace_root": self.workspace_root, "command": coder_out.command or ""}
                    await event_bus.publish(PrerakEvent(
                        conversation_id=convo_id,
                        execution_id=session.execution_id,
                        workspace_root=self.workspace_root,
                        event_type="terminal_started",
                        details={"command": tool_kwargs["command"]}
                    ))
                
                # --- PRE-EXECUTION SNAPSHOT ---
                before_content = ""
                diff_tools = ["write_file", "edit_file", "delete_file"]
                if coder_out.tool in diff_tools and coder_out.path:
                    safe_path = resolve_safe_path(self.workspace_root, coder_out.path)
                    if safe_path.exists() and safe_path.is_file():
                        try:
                            before_content = safe_path.read_text(encoding="utf-8")
                        except Exception:
                            pass

                result = self.executor.execute(coder_out.tool, tool_kwargs)
                
                # --- POST-EXECUTION SNAPSHOT & DIFF GENERATION ---
                if result.success and coder_out.tool in diff_tools and coder_out.path:
                    after_content = ""
                    if safe_path.exists() and safe_path.is_file():
                        try:
                            after_content = safe_path.read_text(encoding="utf-8")
                        except Exception:
                            pass
                            
                    from app.diff.patch_engine import patch_engine
                    diff_patch = patch_engine.generate_diff(coder_out.path, before_content, after_content)
                    
                    if diff_patch:
                        await event_bus.publish(PrerakEvent(
                            conversation_id=convo_id,
                            execution_id=session.execution_id,
                            workspace_root=self.workspace_root,
                            event_type="diff_generated",
                            path=coder_out.path,
                            details={
                                "before": before_content,
                                "after": after_content,
                                "diff": diff_patch
                            }
                        ))
                        
                if coder_out.tool == "execute_terminal":
                    if result.success:
                        await event_bus.publish(PrerakEvent(
                            conversation_id=convo_id,
                            execution_id=session.execution_id,
                            workspace_root=self.workspace_root,
                            event_type="terminal_completed",
                            details={"output": result.output}
                        ))
                    else:
                        await event_bus.publish(PrerakEvent(
                            conversation_id=convo_id,
                            execution_id=session.execution_id,
                            workspace_root=self.workspace_root,
                            event_type="terminal_failed",
                            details={"error": result.error}
                        ))
                
                await event_bus.publish(PrerakEvent(
                    conversation_id=session.convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
                    event_type="tool_completed",
                    tool=coder_out.tool,
                    path=coder_out.path,
                    success=result.success,
                    details={"output": result.output, "error": result.error}
                ))

                if result.success:
                    step_success = True
                    # Record touched file on success
                    if coder_out.path:
                        touched_files.append({"path": coder_out.path, "action": coder_out.tool})
                    break # exit retry loop
                else:
                    error_feedback = result.error
                    if attempt < MAX_RETRIES - 1:
                        await self.log_transition(session, ExecutionState.RECOVERING)
                        # Loop continues to retry
            
            if not step_success:
                await self.log_transition(session, ExecutionState.FAILED)
                await event_bus.publish(PrerakEvent(
                    conversation_id=convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
                    event_type="execution_failed",
                    details={"error": f"Tool execution failed after {MAX_RETRIES} attempts: {error_feedback}"}
                ))
                await self._save_state(session.execution_id, convo_id, prompt, ExecutionState.FAILED.value, False, touched_files)
                return False

        # 4. VERIFYING
        await self.log_transition(session, ExecutionState.VERIFYING)
        await event_bus.publish(PrerakEvent(
            conversation_id=convo_id,
            execution_id=session.execution_id,
            workspace_root=self.workspace_root,
            event_type="verification_started",
            path="all_touched_files"
        ))
        
        # Verify all touched python files
        is_valid = True
        for f in touched_files:
            target_file = resolve_safe_path(self.workspace_root, f["path"])
            if target_file.suffix == '.py':
                if not self.verifier.verify_syntax(str(target_file)):
                    is_valid = False
                    break
        
        await event_bus.publish(PrerakEvent(
            conversation_id=session.convo_id,
            execution_id=session.execution_id,
            workspace_root=self.workspace_root,
            event_type="verification_completed",
            success=is_valid,
            path="all_touched_files"
        ))

        if is_valid:
            await self.log_transition(session, ExecutionState.SUCCESS)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="execution_completed"
            ))
            await self._save_state(session.execution_id, convo_id, prompt, ExecutionState.SUCCESS.value, True, touched_files)
            return True
        else:
            await self.log_transition(session, ExecutionState.FAILED)
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="execution_failed",
                details={"error": "Syntax verification failed"}
            ))
            await self._save_state(session.execution_id, convo_id, prompt, ExecutionState.FAILED.value, False, touched_files)
            return False

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
