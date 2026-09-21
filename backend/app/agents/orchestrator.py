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
from app.agents.analyzer_agent import AnalyzerAgent
from app.agents.observer_agent import ObserverAgent
from app.tools.terminal_tools.execute_terminal import cleanup_background_processes
from app.tools.terminal_tools.tail_process_logs import tail_process_logs
from app.tools.parsers.compiler_parser import parser_registry
from app.context.builder import context_builder
from app.db.database import AsyncSessionLocal
from app.workspace.manager import WorkspaceManager
from app.execution.store import ExecutionStore, ExecutionRecord
from app.execution.action_validator import ActionValidator
from app.execution.plan_validator import PlanValidator
from app.tools.registry import tool_registry
from pathlib import Path
import json
import time

class Orchestrator:
    """The central loop running the deterministic execution pipeline."""
    def __init__(self, workspace_root: str, workspace_id: str):
        self.workspace_root = workspace_root
        self.workspace_id = workspace_id
        self.executor = ToolExecutor()
        self.verifier = PythonVerifier()
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.analyzer = AnalyzerAgent()
        self.observer = ObserverAgent()
        self.action_validator = ActionValidator(tool_registry)
    
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
                    task_type="create_project",
                    success_criteria=["Task completed"],
                    failure_conditions=[],
                    execution_stages=[]
                )
            else:
                max_planner_attempts = 3
                feedback_errors = ""
                planner_out = None
                
                for attempt in range(max_planner_attempts):
                    try:
                        planner_out = await self.planner.decompose_task(
                            user_request=prompt,
                            context_text=context_text,
                            feedback_errors=feedback_errors
                        )
                        # Optionally, we can do additional PlanValidator logic here
                        break
                    except ValueError as e:
                        error_str = str(e)
                        print(f"Planner attempt {attempt+1} failed: {error_str}")
                        
                        corrections = []
                        if "allowed_tools must not be empty" in error_str:
                            corrections.append("- Do not generate completion stages. The orchestrator determines SUCCESS automatically. Every stage must have allowed_tools.")
                        if "no corresponding task in task_queue" in error_str:
                            corrections.append("- Every tool you put in allowed_tools MUST have at least one task in the task_queue using that tool type.")
                        if "contain at least one actionable task" in error_str:
                            corrections.append("- You created an execution stage but left the task_queue empty. You must define executable tasks for it.")
                        if "requires a 'command' field" in error_str:
                            corrections.append("- Your execute_terminal task is missing the 'command' field.")
                        if "requires a 'path' field" in error_str:
                            corrections.append("- Your file-editing task is missing the 'path' field.")
                            
                        feedback_errors = f"Validation Errors:\n{error_str}\n\n"
                        if corrections:
                            feedback_errors += "How to repair:\n" + "\n".join(corrections) + "\n"
                            
                        if attempt == max_planner_attempts - 1:
                            raise e
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

        # 1.5 PLANNER NORMALIZATION
        task_counter = 1
        for stage in planner_out.execution_stages:
            if stage.task_queue:
                for task in stage.task_queue:
                    if task.task_id is None or task.task_id <= 0:
                        task.task_id = task_counter
                        task_counter += 1
                        
        # 2. AUTONOMOUS REACT LOOP
        await self.log_transition(session, ExecutionState.CODING)
        conversation_history = []
        task_description = (
            f"Goal: {planner_out.goal}\n"
            f"Success Criteria:\n" + "\n".join(f"- {c}" for c in planner_out.success_criteria) + "\n\n"
            f"Failure Conditions (BLOCKED if these occur):\n" + "\n".join(f"- {c}" for c in planner_out.failure_conditions) + "\n\n"
            f"Execution Stages:\n" + "\n".join(f"Stage {s.stage_number}: {s.goal} (Allowed tools: {', '.join(s.allowed_tools)})" for s in planner_out.execution_stages)
        )
        
        MAX_ITERATIONS = 15
        final_state = None
        action_memory = {}
        
        # Phase 18: Execution Stages Tracking
        execution_context = {
            "mode": "NORMAL",
            "stages": [s.model_dump() for s in planner_out.execution_stages],
            "current_stage_idx": 0,
            "recovery_sequence": [],
            "recovery_idx": 0,
            "recovery_attempts": 0
        }
        
        import platform
        import os
        import sys
        
        self.execution_store = ExecutionStore(self.workspace_root, session.execution_id)
        
        env_context = f"""
Operating System: {platform.system()} {platform.release()}
Shell: {os.environ.get('COMSPEC', 'cmd.exe')}
Python Executable: {sys.executable}
Workspace Root: {self.workspace_root}
"""
        
        working_memory = {
            "Environment": env_context,
            "Execution Memory": "[]",
            "Current File": None,
            "Last Read File Text": None,
            "Last Terminal Error": None,
            "Last Edit Status": None,
            "Last Observer Feedback": None
        }
        
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
                recent_records = self.execution_store.get_recent_records(5)
                working_memory["Execution Memory"] = json.dumps([r.model_dump() for r in recent_records], indent=2)
                
                coder_context_result = context_builder.build_coder_context(prompt, self.workspace_root, working_memory["Current File"] or "")
                coder_context_text = coder_context_result["formatted_text"]
                
                if execution_context["mode"] == "NORMAL" and execution_context["current_stage_idx"] < len(execution_context["stages"]):
                    cs = execution_context["stages"][execution_context["current_stage_idx"]]
                    total_stages = len(execution_context["stages"])
                    coder_context_text += f"\n\n=== CURRENT STAGE ({cs['stage_number']}/{total_stages}) ===\nGoal: {cs['goal']}\nAllowed Tools: {cs['allowed_tools']}\n"
                    
                    # Phase 24: Queue Management
                    task_queue = cs.get("task_queue", [])
                    pending_tasks = [t for t in task_queue if t.get("status") == "pending"]
                    if pending_tasks:
                        current_task = pending_tasks[0]
                        coder_context_text += f"\n=== CURRENT TASK ===\nType: {current_task.get('type')}\nPath: {current_task.get('path', '')}\nDescription: {current_task.get('description', '')}\n"
                
                coder_out = await self.coder.handle_task(task_description, conversation_history, coder_context_text, working_memory, iteration + 1)
                
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

            # --- DYNAMIC TOOL DISPATCH PREP ---
            tool_kwargs = coder_out.model_extra.copy() if coder_out.model_extra else {}
            
            # PIPELINE LOGGING
            print(f"[PIPELINE LLM OUTPUT]: {coder_out.tool} {json.dumps(tool_kwargs)}")
            
            # Action Memory (Phase 13E)
            import hashlib
            action_string = f"{coder_out.tool}:{json.dumps(tool_kwargs, sort_keys=True)}"
            action_hash = hashlib.md5(action_string.encode()).hexdigest()
            action_memory[action_hash] = action_memory.get(action_hash, 0) + 1
            
            if action_memory[action_hash] == 3:
                # Phase 13E.2: Loop Intervention Prompt
                conversation_history.append({
                    "role": "system",
                    "content": "You have attempted the EXACT same action 3 times. The previous strategy is clearly not working. You MUST choose a completely different tool or explain why the goal cannot be completed. Do not repeat this action again."
                })
                await self.log_transition(session, ExecutionState.RECOVERING)
                continue # Skip executing it a 3rd time, force them to think again
                
            elif action_memory[action_hash] >= 5:
                # Phase 13E.3: Hard Termination
                conversation_history.append({
                    "role": "system", 
                    "content": f"[SYSTEM TERMINATION]: You hit this EXACT SAME ACTION {action_memory[action_hash]} times. Execution aborted to prevent infinite loops."
                })
                final_state = ExecutionState.FAILED
                await event_bus.publish(PrerakEvent(
                    conversation_id=convo_id,
                    execution_id=session.execution_id,
                    workspace_root=self.workspace_root,
                    event_type="execution_failed",
                    details={"error": f"Infinite loop detected on tool {coder_out.tool}. Terminating ReAct."}
                ))
                break  # Terminate the ReAct loop
            
            # --- PIPELINE STAGE 2: ACTION VALIDATOR (Raw LLM Output) ---
            validation = self.action_validator.validate(coder_out.tool, tool_kwargs)
            if not validation.success:
                print(f"[PIPELINE VALIDATION FAILED]: {validation.error_type}: {validation.error}")
                tool_blocked = False
                class GuardResult:
                    success = False
                    output = ""
                    error = validation.error
                result = GuardResult()
                class MockObserverOut:
                    execution = "SCHEMA_VIOLATION"
                    severity = "NONE"
                    verification = "NA"
                    evidence = {}
                    feedback = f"{validation.error_type}: {validation.error}. DO NOT RETRY identical arguments. Read the error and fix the arguments."
                observer_out = MockObserverOut()
                start_time = time.time()
                # Record to conversation history
                safe_log_kwargs = tool_kwargs.copy()
                conversation_history.append({
                    "role": "assistant",
                    "content": json.dumps({"tool": coder_out.tool, **safe_log_kwargs})
                })
            else:
                if validation.repaired:
                    repair_msg = "; ".join(validation.repairs)
                    print(f"[PIPELINE VALIDATION REPAIRED]: {repair_msg}")
                    conversation_history.append({"role": "system", "content": f"[ACTION VALIDATOR REPAIRED]: {repair_msg}"})
                    
                tool_kwargs = validation.kwargs
                print(f"[PIPELINE POST-VALIDATION]: {json.dumps(tool_kwargs)}")
                
                # --- PIPELINE STAGE 3: TOOL GUARD SEQUENCE VALIDATION ---
                tool_blocked = False
                guard_reason = ""
                
                # Phase 24: Duplicate hash protection
                if coder_out.tool in ("write_file", "edit_file"):
                    file_path = tool_kwargs.get("file_path") or tool_kwargs.get("path") or tool_kwargs.get("filename")
                    content = tool_kwargs.get("content") or tool_kwargs.get("new_content")
                    if file_path and content:
                        import hashlib
                        content_hash = hashlib.md5(content.encode()).hexdigest()
                        if "written_files" not in working_memory:
                            working_memory["written_files"] = {}
                        if file_path in working_memory["written_files"] and working_memory["written_files"][file_path] == content_hash:
                            tool_blocked = True
                            guard_reason = f"Duplicate write detected. '{file_path}' already contains these exact contents. Please move on to the next task."
                        else:
                            working_memory["written_files"][file_path] = content_hash
                
                if execution_context["mode"] == "NORMAL":
                    if execution_context["current_stage_idx"] < len(execution_context["stages"]):
                        current_stage = execution_context["stages"][execution_context["current_stage_idx"]]
                        if coder_out.tool not in current_stage["allowed_tools"] and coder_out.tool != "task_completed":
                            tool_blocked = True
                            guard_reason = f"Tool '{coder_out.tool}' is not allowed in current stage (Stage {current_stage['stage_number']}: {current_stage['goal']}). Allowed: {current_stage['allowed_tools']}"
                elif execution_context["mode"] == "RECOVERY":
                    if execution_context["recovery_idx"] < len(execution_context["recovery_sequence"]):
                        expected_tool = execution_context["recovery_sequence"][execution_context["recovery_idx"]]
                        if coder_out.tool != expected_tool:
                            tool_blocked = True
                            guard_reason = f"RECOVERY MODE: Expected '{expected_tool}', but received '{coder_out.tool}'."
                
                # Check for task completion (Fallback if planner adds it, though it's removed)
                if coder_out.tool == "task_completed" and not tool_blocked:
                    status = tool_kwargs.get("status", "success")
                    if status == "success":
                        final_state = ExecutionState.SUCCESS
                    elif status == "blocked":
                        final_state = ExecutionState.BLOCKED
                    else:
                        final_state = ExecutionState.FAILED
                    break
                    
                # 3. EXECUTING
                await self.log_transition(session, ExecutionState.EXECUTING)
                start_time = time.time()
                
                # --- PIPELINE STAGE 4: WORKSPACE INJECTOR ---
                tool_kwargs["workspace_root"] = self.workspace_root
                print(f"[PIPELINE POST-WORKSPACE-INJECT]: {json.dumps(tool_kwargs)}")
                
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
                
                if tool_blocked:
                    # Mock result for blocked tool
                    class GuardResult:
                        success = False
                        output = ""
                        error = f"Tool blocked by Orchestrator. Reason: {guard_reason}"
                    result = GuardResult()
                    observer_out = None
                else:
                    # Execute tool
                    result = self.executor.execute(coder_out.tool, tool_kwargs)
                    # Phase 18: Observer Evaluation
                    try:
                        current_stage = execution_context["stages"][execution_context["current_stage_idx"]] if execution_context["mode"] == "NORMAL" and execution_context["current_stage_idx"] < len(execution_context["stages"]) else {}
                        
                        # Decouple tool success from stage success. The queue IS the state.
                        task_queue = current_stage.get("task_queue", [])
                        pending_tasks = [t for t in task_queue if t.get("status") == "pending"]
                        
                        # We only ask the observer to verify if the tool itself succeeded.
                        expected_success_conditions = [f"Tool {coder_out.tool} executed successfully."]
                            
                        observer_out = await self.observer.observe(coder_out.tool, safe_log_kwargs, result.output or "", result.error or "", expected_success_conditions)
                        working_memory["Last Observer Feedback"] = observer_out.feedback
                    except Exception as e:
                        print(f"Observer failed: {e}")
                        observer_out = None
                    
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Phase 21 ExecutionStore
            record = ExecutionRecord(
                tool=coder_out.tool,
                arguments=safe_log_kwargs,
                stdout=result.output or "",
                stderr=result.error or "",
                classification=observer_out.execution if observer_out else "PENDING",
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                duration_ms=duration_ms,
                stage=execution_context["current_stage_idx"] + 1
            )
            self.execution_store.add_record(record)
                    
            # Phase 14B: Update Working Memory
            if coder_out.tool == "read_file" and result.success:
                working_memory["Current File"] = tool_kwargs.get("path")
                working_memory["Last Read File Text"] = result.output[:200] + "..." if len(result.output) > 200 else result.output
            elif coder_out.tool == "execute_terminal":
                if not result.success:
                    working_memory["Last Terminal Error"] = result.error[:300] + "..." if len(result.error) > 300 else result.error
                else:
                    working_memory["Last Terminal Error"] = "Fixed! Execution successful."
            elif coder_out.tool == "edit_file":
                if result.success:
                    working_memory["Last Edit Status"] = "Success"
                else:
                    working_memory["Last Edit Status"] = f"Failed: {result.error}"
            elif coder_out.tool == "write_file" and result.success:
                working_memory["Last Edit Status"] = "Overwritten File Successfully"
            elif coder_out.tool == "create_project" and result.success:
                try:
                    if hasattr(result, "data") and isinstance(result.data, dict) and "created_files" in result.data:
                        files = "\n".join(result.data["created_files"])
                        working_memory["Workspace Structure"] = f"Created files:\n{files}"
                except Exception as e:
                    print(f"Failed to inject created files into memory: {e}")
                    
            # Parse Diagnostics for Verification Stages
            current_stage = execution_context["stages"][execution_context["current_stage_idx"]] if execution_context["current_stage_idx"] < len(execution_context["stages"]) else {}
            stage_type = current_stage.get("stage_type", "execution")
            verification_kind = current_stage.get("verification_kind", "compile")
            
            if stage_type == "verification" and not result.success and coder_out.tool == "execute_terminal":
                diagnostics = parser_registry.parse_diagnostics(result.error or result.output)
                if diagnostics:
                    if "VerificationContext" not in working_memory:
                        max_attempts = 5 if verification_kind == "compile" else (2 if verification_kind == "tests" else 1)
                        working_memory["VerificationContext"] = {
                            "kind": verification_kind,
                            "attempt": 0,
                            "max_attempts": max_attempts,
                            "history": []
                        }
                    
                    working_memory["VerificationContext"]["attempt"] += 1
                    working_memory["VerificationContext"]["diagnostics"] = diagnostics
                    
                    # Store history snapshot
                    snapshot = [f"{d.get('code', 'ERR')}: {d.get('file', 'unknown')}" for d in diagnostics.get("diagnostics", [])]
                    working_memory["VerificationContext"]["history"].append({
                        "attempt": working_memory["VerificationContext"]["attempt"],
                        "summary": snapshot
                    })
                    
                    # Override terminal error with clean structured diagnostic
                    working_memory["Last Terminal Error"] = f"Static Verification Failed. Diagnostics:\n{diagnostics}"
                    
            elif stage_type == "verification" and result.success and "VerificationContext" in working_memory:
                # Build succeeded!
                working_memory.pop("VerificationContext")
            
            # Phase 18 State Transitions
            if tool_blocked:
                conversation_history.append({"role": "system", "content": f"Error: {result.error}"})
            elif observer_out:
                conversation_history.append({
                    "role": "system", 
                    "content": f"[OBSERVER: {observer_out.execution}] {observer_out.feedback}\nEvidence: {observer_out.evidence}"
                })
                
                if observer_out.verification == "VERIFIED" or observer_out.execution in ["SUCCESS", "LONG_RUNNING", "SERVER_READY", "HTTP_READY", "VERIFIED"]:
                    if execution_context["mode"] == "NORMAL":
                        # Mark task complete if tool succeeded
                        if pending_tasks:
                            pending_tasks[0]["status"] = "completed"
                            
                        # Re-evaluate pending tasks
                        has_pending = any(t.get("status") == "pending" for t in current_stage.get("task_queue", []))
                        
                        if has_pending:
                            # Queue not empty, continue coding!
                            pass
                        else:
                            # Queue is empty, stage is complete. Advance automatically.
                            execution_context["current_stage_idx"] += 1
                            if execution_context["current_stage_idx"] >= len(execution_context["stages"]):
                                final_state = ExecutionState.SUCCESS
                                break
                    else:
                        execution_context["recovery_idx"] += 1
                        if execution_context["recovery_idx"] >= len(execution_context["recovery_sequence"]):
                            execution_context["mode"] = "NORMAL"
                
                elif observer_out.execution == "SCHEMA_VIOLATION":
                    # Bypass Analyzer and recovery budget; return straight to Coder
                    conversation_history.append({"role": "system", "content": f"Tool schema violation: {observer_out.feedback}"})
                
                elif observer_out.execution in ["FAILURE", "BLOCKED", "RECOVERABLE"]:
                    
                    if stage_type == "verification" and coder_out.tool == "execute_terminal" and "VerificationContext" in working_memory:
                        vc = working_memory["VerificationContext"]
                        if vc["attempt"] > vc["max_attempts"]:
                            conversation_history.append({"role": "system", "content": f"Verification budget exceeded ({vc['attempt']}/{vc['max_attempts']})."})
                            final_state = ExecutionState.FAILED
                            break
                        else:
                            # Keep mode NORMAL, just append feedback and let coder fix it
                            conversation_history.append({"role": "system", "content": f"Verification attempt {vc['attempt']}/{vc['max_attempts']} failed. Please repair the code based on the compiler diagnostics."})
                            continue
                            
                    fingerprint = f"{coder_out.tool}_{observer_out.execution}_{execution_context['current_stage_idx']}"
                    last_fingerprint = execution_context.get("last_error_fingerprint")
                    execution_context["last_error_fingerprint"] = fingerprint
                    
                    if execution_context["mode"] == "NORMAL":
                        execution_context["mode"] = "RECOVERY"
                        execution_context["recovery_attempts"] = 1
                    else:
                        # Even if the error is exactly the same, let's increment and retry instead of instant 99
                        execution_context["recovery_attempts"] += 1
                        
                    if execution_context["recovery_attempts"] > 3 or observer_out.severity == "FATAL":
                        # Extract the underlying error for better diagnostics
                        err_detail = result.error if (result and hasattr(result, "error") and result.error) else observer_out.feedback
                        msg = f"Recovery budget exceeded ({execution_context['recovery_attempts']}/3) or FATAL error.\nTool: {coder_out.tool}\nError: {err_detail}"
                        
                        conversation_history.append({"role": "system", "content": msg})
                        final_state = ExecutionState.FAILED
                        await event_bus.publish(PrerakEvent(
                            conversation_id=convo_id,
                            execution_id=session.execution_id,
                            workspace_root=self.workspace_root,
                            event_type="execution_failed",
                            details={"error": msg}
                        ))
                        break
                        
                    await self.log_transition(session, ExecutionState.RECOVERING)
                    try:
                        analysis_out = await self.analyzer.analyze(result.error or observer_out.feedback, working_memory["Current File"] or "")
                        execution_context["recovery_sequence"] = analysis_out.recovery_sequence
                        execution_context["recovery_idx"] = 0
                        conversation_history.append({
                            "role": "system", 
                            "content": f"[ANALYZER DIAGNOSIS]: {analysis_out.diagnosis}\n[NEW RECOVERY SEQUENCE]: {analysis_out.recovery_sequence}"
                        })
                    except Exception as e:
                        conversation_history.append({"role": "system", "content": f"[ANALYZER FAILED]: {str(e)}"})
            else:
                # Fallback if observer is completely broken
                if result.success:
                    conversation_history.append({"role": "system", "content": f"Success: {result.output}"})
                else:
                    conversation_history.append({"role": "system", "content": f"Error: {result.error}"})
                
            await event_bus.publish(PrerakEvent(
                conversation_id=session.convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="tool_completed",
                tool=coder_out.tool,
                success=result.success,
                details={"output": result.output, "error": result.error}
            ))

        if not final_state:
            final_state = ExecutionState.FAILED
            await event_bus.publish(PrerakEvent(
                conversation_id=convo_id,
                execution_id=session.execution_id,
                workspace_root=self.workspace_root,
                event_type="execution_failed",
                details={"error": "Max iterations reached without task_completed"}
            ))

        # 4. COMPLETION
        await self.log_transition(session, final_state)
        
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
            
        is_success = final_state == ExecutionState.SUCCESS
        await self._save_state(session.execution_id, convo_id, prompt, final_state.value, is_success, touched_files)
        
        # Phase 21: Auto cleanup
        try:
            from app.execution.process_manager import process_manager
            process_manager.cleanup()
        except:
            cleanup_background_processes()
            
        return is_success

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
