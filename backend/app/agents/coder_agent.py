import json
from app.runtime.model_router import model_router
from app.runtime.model_router import ModelRouter
from app.models.schemas import CoderOutput

from app.tools.registry import tool_registry

class CoderAgent:
    """The powered agent responsible for writing code and making tool calls."""
    
    async def handle_task(self, task_description: str, conversation_history: list[dict], context_text: str = "", working_memory: dict = None, iteration: int = 1) -> CoderOutput:
        model = ModelRouter.get_coder_model()
        
        tool_schemas = json.dumps(tool_registry.get_all_tool_schemas(), indent=2)
        
        system_prompt = (
            "You are a strict Coder Agent running in an autonomous ReAct loop.\n"
            "You MUST output pure JSON containing ONLY the tool call.\n"
            "Format: { 'tool': '<tool_name>', '<arg_name>': '<arg_value>', ... }\n\n"
            "EXECUTION CONTRACT:\n"
            "- The Planner sequence is authoritative. You must execute tools ONLY in the provided order.\n"
            "- You cannot skip steps, add steps, or replace tools.\n"
            "- The Orchestrator enforces this sequence. Out-of-order tools will be rejected.\n"
            "- Allowed deviation: tool failure or unavailable tool (if deviation is required, explain why).\n\n"
            "FILE MODIFICATION POLICY:\n"
            "- Before modifying a file: IF file exists, MUST call `read_file` first.\n"
            "- Exceptions: `create_file` operation, or complete file content already exists in current context.\n"
            "- For existing files: `edit_file` is preferred.\n"
            "- `write_file` is forbidden unless: creating a new file, or replacing the entire file is explicitly requested.\n\n"
            "REASONING LOOP:\n"
            "1. Understand goal and suggested strategy.\n"
            "2. Choose tool.\n"
            "3. Execute tool.\n"
            "4. Observe result.\n"
            "5. Exit Reasoning - Ask yourself:\n"
            "   - 'Can I continue working?' -> Choose next tool.\n"
            "   - 'Are the success criteria met?' -> Call `verify_goal`, then `task_completed(status=\"success\")`.\n"
            "   - 'Is the task permanently blocked (e.g. security policy, missing dependency, nonexistent command)?' -> Call `task_completed(status=\"blocked\", summary=\"...\", evidence=[...])`.\n"
            "   - 'Did the task fundamentally fail?' -> Call `task_completed(status=\"failed\", summary=\"...\", evidence=[...])`.\n\n"
            "COMMON TASK PATTERNS:\n"
            "Rename File: list_files -> read_file -> write_file -> delete_file -> search_code_exact -> verify_goal -> task_completed\n"
            "Create File: write_file -> verify_goal -> task_completed\n"
            "Fix Bug: read_file -> edit_file -> execute_terminal -> verify_goal -> task_completed\n\n"
            f"AVAILABLE TOOLS:\n{tool_schemas}\n\n"
            "CRITICAL RULES:\n"
            "- ENVIRONMENT: Operating System: Windows. Shell: CMD/Powershell. Do NOT use Linux bash syntax.\n"
            "- Do NOT use: source, chmod, apt-get, rm, /bin/.\n"
            "- To find a file by its name, you MUST use `list_files`.\n"
            "- To find specific code or text INSIDE a file, you MUST use `search_code_exact`.\n"
            "- EXECUTION-FIRST: When asked to fix an execution error, you MUST `execute_terminal` FIRST to observe the error, before modifying any code.\n"
            "- FAITHFULNESS: When fixing errors, preserve original behavior exactly. Make the SMALLEST possible change that satisfies the goal.\n"
            "- DO NOT rewrite working code. DO NOT refactor. DO NOT change string outputs or variable names unless explicitly required to fix the error.\n"
            "- GOAL VERIFICATION: You MUST call `verify_goal` BEFORE calling `task_completed(status=\"success\")`. Your verification MUST compare intended behavior with actual behavior.\n"
            "- EVIDENCE-BASED COMPLETION: Do not call `task_completed(status=\"success\")` unless you have explicit terminal output proving success.\n\n"
            "RECOVERY RULES:\n"
            "- If `edit_file` fails: 1. Look at the `WORKSPACE CONTEXT` block to see the exact current file state, 2. ensure your `old_content` matches perfectly, 3. retry edit. 4. If it fails again, use `write_file` to completely overwrite the entire file with the correct contents.\n"
            "- ENVIRONMENT AND DEPENDENCY RECOVERY: If you encounter an `ImportError` or `ModuleNotFoundError` during execution, or if a pip install loop occurs, you MUST analyze the package versions (e.g., read requirements.txt, or use `execute_terminal` to run `pip list`) to check for compatibility conflicts before retrying installation. Do not blindly repeat the exact same `pip install` command.\n\n"
            "Do NOT include markdown blocks, prose, or explanations. Only return valid JSON."
        )
        
        # Phase 14D: Truncate Planner strategy after Iteration 2
        if iteration > 2:
            task_description = f"Current Goal: {task_description.split('Success Criteria:')[0].replace('Goal:', '').strip()}\n(Strategy omitted to save context - focus on fixing immediate errors)"
            
        # Phase 14A: Conversation Compression
        history_block = ""
        recent_turns = conversation_history[-4:] if len(conversation_history) >= 4 else conversation_history
        older_turns = conversation_history[:-4] if len(conversation_history) >= 4 else []
        
        for turn in older_turns:
            if turn["role"] == "assistant":
                try:
                    t = json.loads(turn['content'])
                    history_block += f"[Past] Used: {t.get('tool')}\n"
                except:
                    history_block += f"[Past] Action Attempted\n"
            elif turn["role"] == "system":
                history_block += f"[Past] Result: (truncated)\n"
                
        for turn in recent_turns:
            if turn["role"] == "assistant":
                history_block += f"\n[Recent] YOU CALLED TOOL:\n{turn['content']}\n"
            elif turn["role"] == "system":
                content = turn['content']
                if len(content) > 800:
                    content = content[:400] + "\n...[TRUNCATED]...\n" + content[-400:]
                history_block += f"[Recent] TOOL RESULT:\n{content}\n"
                
        # Phase 14B: Deterministic Working Memory
        wm_block = ""
        if working_memory:
            wm_block = "=== WORKING MEMORY (FACTS) ===\n"
            for k, v in working_memory.items():
                if v: wm_block += f"{k}: {v}\n"
            wm_block += "\n"
                
        prompt = (
            f"Task:\n{task_description}\n\n"
            f"{wm_block}"
            f"=== WORKSPACE CONTEXT ===\n{context_text}\n\n"
            f"=== EXECUTION HISTORY ===\n{history_block if history_block else 'No tools called yet.'}\n\n"
            "Analyze Working Memory, history and context. Decide the next step. Provide the exact tool call JSON."
        )
        
        print(f"\n--- CODER DIAGNOSTIC ---")
        print(f"Model: {model}")
        print(f"Prompt chars: {len(prompt)}, words: {len(prompt.split())}")
        print(f"System chars: {len(system_prompt)}, words: {len(system_prompt.split())}")
        print(f"--------------------------\n")
        
        response = await model_router.generate(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        # Validate early
        try:
            data = json.loads(response)
            return CoderOutput(**data)
        except Exception as e:
            raise ValueError(f"Coder output validation failed: {str(e)} | Output: {response}")
