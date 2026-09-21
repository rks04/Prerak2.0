import json
from app.runtime.model_router import model_router
from app.runtime.model_router import ModelRouter
from app.models.schemas import PlannerOutput

class PlannerAgent:
    """The llama3.1:8b powered agent responsible for task decomposition."""
    
    async def decompose_task(self, user_request: str, context_text: str = "", feedback_errors: str = "") -> PlannerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are the High-Level Architect for an autonomous AI coding agent.\n"
            "Your job is to understand the user's prompt and define the specific goal, the task type, the success criteria, the exact failure conditions, and an advisory suggested strategy for the Coder agent.\n"
            "You MUST output pure JSON matching exactly:\n"
            "{\n"
            "  'goal': 'A clear description of what needs to be built/fixed',\n"
            "  'task_type': 'MUST ONLY BE: create_project OR modify_existing',\n"
            "  'success_criteria': ['A list', 'of testable', 'criteria'],\n"
            "  'failure_conditions': ['A list', 'of blocking conditions', 'e.g. security policy', 'dependency unavailable'],\n"
            "  'execution_stages': [\n"
            "    {\n"
            "      'stage_number': 1,\n"
            "      'goal': 'Generate Product Module',\n"
            "      'allowed_tools': ['write_file', 'edit_file'],\n"
            "      'completion_condition': 'SUCCESS',\n"
            "      'success_conditions': ['Files created'],\n"
            "      'task_queue': [\n"
            "        {'task_id': 1, 'type': 'write_file', 'path': 'src/product/entity.ts', 'description': 'Database entity', 'status': 'pending'},\n"
            "        {'task_id': 2, 'type': 'write_file', 'path': 'src/product/service.ts', 'description': 'Business logic', 'status': 'pending'}\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "CRITICAL RULES:\n"
            "- Do not write the code. Just define the plan.\n"
            "- The `execution_stages` must logically progress from creation to execution to verification to completion.\n"
            "- NEVER invent new files, new names, or complex refactors unless the user explicitly asks for them. Keep the sequence minimal and strictly focused on the exact prompt.\n"
            "- WORKSPACE AWARENESS: Before scheduling `create_project`, inspect the workspace. If the workspace already contains a recognizable project (e.g., `package.json`, `Cargo.toml`, `go.mod`, `requirements.txt`, `pyproject.toml`), assume the project exists unless a new one is explicitly requested. Prefer an edit/update plan.\n"
            "- EXISTING FILE AWARENESS: If required files already exist, schedule edit operations instead of write operations unless replacement is explicitly required.\n"
            "- FRAMEWORK CONVENTIONS: Register components in the canonical location for the detected framework. Do not invent alternate locations. (e.g., in NestJS, register modules in `app.module.ts`, bootstrap in `main.ts`).\n"
            "- FRAMEWORK KNOWLEDGE (NestJS): 1) `PartialType` -> `@nestjs/mapped-types`. 2) `ValidationPipe` -> `@nestjs/common`. 3) DTO decorators -> `class-validator`. Never import `PartialType` from `class-validator`.\n"
            "- CANONICAL FILENAME: Once you emit a filename/path, every later stage MUST reference that exact path unless an explicit rename is planned. Never invent a new filename later (e.g., if you choose `module.ts`, don't use `product.module.ts` later).\n"
            "- DEPENDENCY PLANNING: Before generating code that imports external packages, verify those dependencies are planned for installation. Schedule a single dependency installation step before writing files that require them.\n"
            "- If a framework is requested and no existing project is detected, you MUST use `create_project` in the first stage. NEVER generate framework boilerplate or package.json manually using `write_file`.\n"
            "- STAGE CONSOLIDATION: Maximum execution stages: 4. Typical project: Stage 1) Scaffold project. Stage 2) Generate feature files (all related feature files MUST be generated in one execution stage). Stage 3) Update configuration/register modules. Stage 4) Install dependencies (if required). STOP.\n"
            "- NON-NEGOTIABLE FORBIDDEN COMMANDS: DO NOT run `npm run build`, `npm start`, `npm run start:dev`, execute `curl`, or execute any HTTP requests. These are forbidden in the planner. Remove them from the plan.\n"
            "- NEVER create a 'Task complete', 'Done', 'Final', or 'Completion' stage. The orchestrator determines completion automatically after the last executable stage.\n"
            "- You MUST define a concrete `task_queue` for EVERY execution stage. The queue must NOT be empty.\n"
            "- EXPLICIT DIFFERENTIATION: Planner.task_type MUST ONLY be 'create_project' or 'modify_existing'. Task.type (inside task_queue) MUST ONLY be 'write_file', 'edit_file', 'delete_file', 'read_file', 'execute_terminal', or 'list_files'.\n"
            "- INVALID STAGE EXAMPLE: {'stage_number': 1} (Missing task_queue)\n"
            "- VALID STAGE EXAMPLE: {'stage_number': 1, 'task_queue': [{'type': 'write_file', 'path': 'src/app.ts', 'description': 'Main app'}]}\n"
            "- The `success_conditions` MUST explicitly list the exact files expected to exist upon stage completion (e.g., ['src/product/entity.ts', 'src/product/service.ts']). Do NOT use vague conditions like 'module.ts created'. The orchestrator will check these exact strings.\n"
            "- The `allowed_tools` MUST ONLY contain valid tools: ['write_file', 'read_file', 'edit_file', 'delete_file', 'list_files', 'execute_terminal', 'search_code_semantic', 'search_code_exact', 'http_request', 'create_project', 'tail_process_logs']. Do NOT invent tool names like 'create_file'.\n"
            "- STATIC VERIFICATION: You MUST append one or more verification stages appropriate for the detected framework (e.g. `npm run build` for React/NestJS, `tsc --noEmit` for TS libs, `python -m py_compile` for Python, `go build`, `cargo check`, etc.). Do NOT start a server or make HTTP requests in this stage.\n"
            "- For verification stages, you MUST set `stage_type` to \"verification\", `verification_kind` to \"compile\", `lint`, or `tests\", and `expected_exit_code` to 0. Set `expected_errors` to 0 if applicable.\n"
            "- For HTTP/API verification: Prefer `http_request`. Do not use `execute_terminal` with `curl` unless explicitly required.\n"
        )
        
        print(f"\n--- PLANNER DIAGNOSTIC ---")
        print(f"Model: {model}")
        print(f"Prompt chars: {len(user_request)}, words: {len(user_request.split())}")
        print(f"System chars: {len(system_prompt)}, words: {len(system_prompt.split())}")
        print(f"--------------------------\n")
        
        full_prompt = f"=== WORKSPACE CONTEXT ===\n{context_text}\n\n=== USER REQUEST ===\n{user_request}"
        
        if feedback_errors:
            full_prompt += f"\n\n=== REPAIR REQUIRED ===\nYour previous JSON was rejected. Fix ONLY the validation errors below. Do not rewrite unrelated stages.\n\n{feedback_errors}\nReturn ONLY the corrected JSON."
        
        response = await model_router.generate(
            model=model,
            prompt=full_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        # Validate early
        print("===== RAW PLANNER RESPONSE =====")
        print(response)
        print("================================")
        try:
            data = json.loads(response)
            
            # Automatically strip trailing Completion stages
            if "execution_stages" in data:
                stages = data["execution_stages"]
                while stages:
                    last = stages[-1]
                    # If it has no tools/tasks and looks like a completion marker
                    if not last.get("allowed_tools") and not last.get("task_queue"):
                        goal = last.get("goal", "").lower()
                        if any(word in goal for word in ["complete", "completed", "done", "finish", "final", "success"]):
                            stages.pop()
                        else:
                            break
                    else:
                        break
                        
            return PlannerOutput(**data)
        except Exception as e:
            raise ValueError(f"{str(e)}")
