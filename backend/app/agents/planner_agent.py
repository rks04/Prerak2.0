import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import PlannerOutput

class PlannerAgent:
    """The llama3.1:8b powered agent responsible for task decomposition."""
    
    async def decompose_task(self, user_request: str, context_text: str = "") -> PlannerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are an expert AI Planner for a local coding agent. "
            "Your ONLY job is to decompose the user's task into a strictly ordered JSON array of tool calls. "
            "You MUST output pure JSON matching exactly: "
            "{ 'goal': 'string', 'steps': [ { 'step': int, 'action': 'string', 'path': 'optional relative path', 'command': 'optional shell command' } ] }. "
            "IMPORTANT: The 'action' in each step MUST be exactly one of: ['write_file', 'edit_file', 'delete_file', 'list_files', 'execute_terminal', 'read_file'].\n"
            "CRITICAL RULES:\n"
            "- Operating System: Windows. If you use 'execute_terminal', provide Windows CMD/Powershell compatible commands only (e.g. no source, no chmod, no /bin/ bash scripts).\n"
            "- Minimize steps: Do NOT overcomplicate. If the user asks to run a script, just run it. Do NOT create virtual environments or run multi-step setups unless explicitly asked.\n"
            "- If the user explicitly specifies a filename in their prompt, you may ONLY modify that filename. Never edit similarly named files in the workspace."
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
