import json
from app.runtime.model_router import model_router
from app.runtime.model_router import ModelRouter
from app.models.schemas import PlannerOutput

class PlannerAgent:
    """The llama3.1:8b powered agent responsible for task decomposition."""
    
    async def decompose_task(self, user_request: str, context_text: str = "") -> PlannerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are the High-Level Architect for an autonomous AI coding agent.\n"
            "Your job is to understand the user's prompt and define the specific goal, the task type, the success criteria, the exact failure conditions, and an advisory suggested strategy for the Coder agent.\n"
            "You MUST output pure JSON matching exactly:\n"
            "{\n"
            "  'goal': 'A clear description of what needs to be built/fixed',\n"
            "  'task_type': 'One of: create_file, edit_file, rename_file, execute_and_fix, search, refactor',\n"
            "  'success_criteria': ['A list', 'of testable', 'criteria'],\n"
            "  'failure_conditions': ['A list', 'of blocking conditions', 'e.g. security policy', 'dependency unavailable'],\n"
            "  'tool_sequence': ['read_file', 'edit_file', 'execute_terminal', 'verify_goal', 'task_completed']\n"
            "}\n"
            "CRITICAL RULES:\n"
            "- Do not write the code. Just define the plan.\n"
            "- The `task_type` dictates the `tool_sequence`. For example, if task_type is 'execute_and_fix', the sequence MUST be strictly: ['execute_terminal', 'read_file', 'edit_file', 'execute_terminal', 'verify_goal', 'task_completed'].\n"
            "- NEVER invent new files, new names, or complex refactors unless the user explicitly asks for them. Keep the sequence minimal and strictly focused on the exact prompt."
        )
        
        print(f"\n--- PLANNER DIAGNOSTIC ---")
        print(f"Model: {model}")
        print(f"Prompt chars: {len(user_request)}, words: {len(user_request.split())}")
        print(f"System chars: {len(system_prompt)}, words: {len(system_prompt.split())}")
        print(f"--------------------------\n")
        
        response = await model_router.generate(
            model=model,
            prompt=user_request,
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        # Validate early
        try:
            data = json.loads(response)
            return PlannerOutput(**data)
        except Exception as e:
            raise ValueError(f"Planner output validation failed: {str(e)} | Output: {response}")
