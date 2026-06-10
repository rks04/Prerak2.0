import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import PlannerOutput

class PlannerAgent:
    """The llama3.1:8b powered agent responsible for task decomposition."""
    
    async def decompose_task(self, user_request: str, context_text: str = "") -> PlannerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are a fast Planning Agent. "
            "Output pure JSON matching: "
            "{ 'goal': 'string', 'steps': [ { 'step': int, 'action': 'string', 'path': 'relative_path' } ] }. "
            "Valid actions: ['read_file', 'write_file', 'edit_file', 'list_files']. "
            "Do NOT include explanations. Only return valid JSON."
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
