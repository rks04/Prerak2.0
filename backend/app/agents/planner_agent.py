import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import PlannerOutput

class PlannerAgent:
    """The llama3.1:8b powered agent responsible for task decomposition."""
    
    async def decompose_task(self, user_request: str, context_text: str = "") -> PlannerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are the High-Level Architect for an autonomous AI coding agent.\n"
            "Your job is to understand the user's prompt and define the specific goal, the success criteria, and an advisory suggested strategy for the Coder agent.\n"
            "You MUST output pure JSON matching exactly:\n"
            "{\n"
            "  'goal': 'A clear description of what needs to be built/fixed',\n"
            "  'success_criteria': ['A list', 'of testable', 'criteria'],\n"
            "  'suggested_strategy': ['Locate original file', 'Create renamed file', 'Remove old file', 'Update references', 'Verify completion']\n"
            "}\n"
            "CRITICAL RULES:\n"
            "- Do not write the code. Just define the plan.\n"
            "- Success criteria must be testable (e.g. 'Server starts on port 8000', 'File app.py exists', 'Tests pass').\n"
            "- The suggested_strategy should be a high-level list of actions the Coder should take. Do NOT output rigid commands."
        )
        
        print(f"\n--- PLANNER DIAGNOSTIC ---")
        print(f"Model: {model}")
        print(f"Prompt chars: {len(user_request)}, words: {len(user_request.split())}")
        print(f"System chars: {len(system_prompt)}, words: {len(system_prompt.split())}")
        print(f"--------------------------\n")
        
        response = await ollama_client.generate(
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
