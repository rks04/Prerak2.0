import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import CoderOutput

class CoderAgent:
    """The qwen2.5-coder:7b powered agent responsible for writing code and making tool calls."""
    
    async def handle_task(self, task_description: str, step_action: str, step_path: str, context_text: str = "") -> CoderOutput:
        model = ModelRouter.get_coder_model()
        system_prompt = (
            "You are a strict Coder Agent. "
            "Your ONLY job is to output pure JSON matching the exact schema: "
            "{ 'tool': 'string', 'path': 'relative string', 'content': 'optional string', 'old_content': 'optional string', 'new_content': 'optional string' }. "
            "IMPORTANT: The 'tool' MUST be exactly one of the following: "
            "['read_file', 'write_file', 'edit_file', 'list_files']. "
            "IMPORTANT: All 'path' values MUST be relative to the workspace root. Do NOT use absolute paths like /home/user/. "
            "CRITICAL RULES FOR edit_file:\n"
            "- You MUST provide 'old_content' matching EXACTLY what is currently in the file based on the context.\n"
            "- You MUST provide 'new_content' with the replacement string.\n"
            "Example: { \"tool\": \"edit_file\", \"path\": \"hello.py\", \"old_content\": \"print('Hello World')\", \"new_content\": \"print('Hello PRERAK')\" }\n\n"
            "Do NOT include markdown blocks, prose, or explanations. Only return valid JSON."
        )
        
        prompt = (
            f"Task: {task_description}\nCurrent Step Action: {step_action}\nPath: {step_path}\n\n"
            f"=== WORKSPACE CONTEXT ===\n{context_text}\n\n"
            "Provide the exact tool call JSON."
        )
        
        response = await ollama_client.generate(
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
