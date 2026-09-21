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
            "1. Read the `=== CURRENT TASK ===` provided by the Orchestrator.\n"
            "2. Read dependencies if necessary.\n"
            "3. Execute the exact tool required for the current task.\n"
            "4. Do NOT attempt to guess the next task. The Orchestrator manages the queue.\n\n"
            "COMMON TASK PATTERNS:\n"
            "Rename File: read_file -> write_file -> delete_file -> search_code_exact\n"
            "Create File: write_file\n"
            "Fix Bug: read_file -> edit_file -> execute_terminal (verification)\n\n"
            f"AVAILABLE TOOLS:\n{tool_schemas}\n\n"
            "CRITICAL RULES:\n"
            "- ENVIRONMENT: Operating System: Windows. Shell: CMD/Powershell. Do NOT use Linux bash syntax.\n"
            "- SCHEMA ENFORCEMENT: Never invent parameter values. If a tool schema contains an enum, you must use one of the listed values exactly.\n"
            "- HTTP/API VERIFICATION: Never use `curl` when `http_request` can accomplish the task.\n"
            "- Use `execute_terminal` ONLY for: python, pip, git, npm, docker.\n"
            "- Use `http_request` for: GET, POST, PUT, PATCH, DELETE.\n"
            "- Do NOT use: source, chmod, apt-get, rm, /bin/.\n"
            "- To find a file by its name, you MUST use `list_files`.\n"
            "- To find specific code or text INSIDE a file, you MUST use `search_code_exact`.\n"
            "- EXECUTION-FIRST: When asked to fix an execution error, you MUST `execute_terminal` FIRST to observe the error, before modifying any code.\n"
            "- FAITHFULNESS: When fixing errors, preserve original behavior exactly. Make the SMALLEST possible change that satisfies the goal.\n"
            "- DO NOT rewrite working code. DO NOT refactor. DO NOT change string outputs or variable names unless explicitly required to fix the error.\n"
            "- LONG-RUNNING PROCESSES: For long-running processes (Flask, FastAPI, Node, React, npm start, uvicorn, etc.), you MUST call `execute_terminal` with `mode=\"background\"`. Do not use any other mode value like \"async\" or \"detached\".\n\n"
            "RECOVERY RULES:\n"
            "- If `edit_file` fails: 1. Look at the `WORKSPACE CONTEXT` block to see the exact current file state, 2. ensure your `old_content` matches perfectly, 3. retry edit. 4. If it fails again, use `write_file` to completely overwrite the entire file with the correct contents.\n"
            "- ENVIRONMENT AND DEPENDENCY RECOVERY: If you encounter an `ImportError` or `ModuleNotFoundError` during execution, you MUST analyze the package versions to check for compatibility conflicts. Do NOT use `pip install <package>` directly to fix version conflicts. You MUST use `edit_file` on `requirements.txt` to enforce the correct versions, then run `pip install -r requirements.txt`.\n"
            "- COMPILER DIAGNOSTICS RECOVERY: If Static Verification fails, do NOT blindly rewrite files. Instead: 1. Parse compiler diagnostics carefully. 2. Group diagnostics by file. 3. Fix the highest priority file/error first. Priority order: (1) Missing imports (2) Missing packages (3) Syntax errors (4) Wrong exports (5) Type mismatches (6) Validation decorators (7) Dead code. Read ONLY the affected files, produce minimal edits, and allow the orchestrator to re-run verification.\n"
            "- If scaffolding a framework fails via `create_project`, NEVER silently substitute a different framework. Report failure (or `task_completed` with `status=failed`).\n"
            "- STRICT QUEUE RECOVERY: When recovering from a failed write, DO NOT attempt to `list_files`, `mkdir`, or guess your place. Simply read the `=== CURRENT TASK ===` and write that exact file again. The queue is your source of truth.\n"
            "- MANDATORY READ-BEFORE-EDIT: Never guess file contents. Before every `edit_file`, you MUST use `read_file` to obtain the exact current file contents. Use the exact returned contents as the edit baseline.\n"
            "- RESPECT EXPLICIT ARCHITECTURE: Do not introduce technologies that contradict explicit user requirements (e.g. 'No database' means no ORM, 'No Docker' means no Dockerfile).\n"
            "- FRAMEWORK HALLUCINATION PREVENTION: Never guess framework APIs. Consult existing imports. For NestJS specifically, you MUST follow these rules exactly:\n"
            "  1. `PartialType` MUST be imported from `@nestjs/mapped-types` or `@nestjs/swagger`. NEVER from `class-validator`.\n"
            "  2. `ValidationPipe` MUST be imported from `@nestjs/common`.\n"
            "  3. DTO decorators (e.g. `@IsString()`) MUST be imported from `class-validator`.\n"
            "  4. `plainToInstance` MUST be imported from `class-transformer`.\n"
            "- DEPENDENCY CONSISTENCY: Every imported external symbol must belong to an installed package.\n"
            "- COMPILATION AWARENESS: Review generated imports, exported symbols, and type references for consistency before declaring completion.\n"
            "- GENERATION CHECKLIST: Before returning SUCCESS verify mentally: 1) Every import exists. 2) Every referenced file exists. 3) Every exported class exists. 4) Every dependency is installed. 5) No generated code contradicts the prompt. 6) All framework conventions are respected. 7) Files being edited were read first.\n"
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
