import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import CoderOutput

class CoderAgent:
    """The qwen2.5-coder:7b powered agent responsible for writing code and making tool calls."""
    
    async def handle_task(self, task_description: str, step_action: str, step_path: str, context_text: str = "", error_feedback: str = None) -> CoderOutput:
        model = ModelRouter.get_coder_model()
        system_prompt = (
            "You are a strict Coder Agent. "
            "Your ONLY job is to output pure JSON matching the exact schema: "
            "{ 'tool': 'string', 'path': 'optional relative string', 'content': 'optional string', 'old_content': 'optional string', 'new_content': 'optional string', 'command': 'optional shell command' }. "
            "IMPORTANT: The 'tool' MUST be exactly one of the following: "
            "['read_file', 'write_file', 'edit_file', 'list_files', 'execute_terminal']. "
            "IMPORTANT: All 'path' values MUST be relative to the workspace root. Do NOT use absolute paths like /home/user/. "
            "CRITICAL RULES FOR edit_file:\n"
            "- You MUST provide 'old_content' matching EXACTLY what is currently in the file based on the context.\n"
            "- You MUST provide 'new_content' with the replacement string.\n"
            "CRITICAL RULES FOR execute_terminal:\n"
            "- ENVIRONMENT: Operating System: Windows. Shell: CMD/Powershell. Do NOT use Linux bash syntax.\n"
            "- Do NOT use: source, chmod, apt-get, rm, /bin/.\n"
            "- Do NOT chain commands with && unless absolutely necessary.\n"
            "- You MUST provide the exact Windows-compatible shell command to run in the 'command' field.\n"
            "Example: { \"tool\": \"execute_terminal\", \"command\": \"pytest test_hello.py\" }\n\n"
            "Do NOT include markdown blocks, prose, or explanations. Only return valid JSON."
        )
        
        feedback_block = ""
        if error_feedback:
            feedback_block = f"\n=== PREVIOUS ATTEMPT FAILED ===\nError:\n{error_feedback}\n\nYou MUST fix your mistake and try again using the correct parameters or command.\n"
            
        prompt = (
            f"Task: {task_description}\nCurrent Step Action: {step_action}\nPath: {step_path}\n"
            f"{feedback_block}\n"
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
