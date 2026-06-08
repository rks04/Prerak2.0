import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import PlannerOutput

class PlannerAgent:
    """The llama3.1:8b powered agent responsible for task decomposition."""
    
    async def decompose_task(self, user_request: str, context_text: str = "") -> PlannerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are a strict Planner Agent. "
            "Your ONLY job is to output pure JSON matching the exact schema: "
            "{ 'goal': 'string', 'steps': [ { 'step': int, 'action': 'string', 'path': 'relative string' } ] }. "
            "IMPORTANT: The 'action' MUST be one of the following tools: "
            "['read_file', 'write_file', 'edit_file', 'list_files']. "
            "IMPORTANT: All 'path' values MUST be relative to the workspace root. Do NOT use absolute paths like /home/user/. "
            "Do NOT hallucinate tools like 'touch'. "
            "Do NOT include markdown blocks, prose, or explanations. Only return valid JSON.\n\n"
            "=== WORKSPACE CONTEXT ===\n"
            "Below is the current workspace context. Use this to understand existing files and recent history before planning:\n"
            f"{context_text}"
        )
        
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
