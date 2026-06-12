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
            "You MUST output pure JSON containing ONLY the tool call. "
            "Format: { 'tool': 'string', 'path': 'optional string', 'content': 'optional string', 'old_content': 'optional string', 'new_content': 'optional string', 'command': 'optional string', 'query': 'optional string' }. "
            "IMPORTANT: 'tool' MUST be one of: ['write_file', 'edit_file', 'delete_file', 'list_files', 'execute_terminal', 'read_file', 'search_code'].\n\n"
            "CRITICAL RULES FOR search_code:\n"
            "- You MUST provide 'query' to search for code.\n"
            "CRITICAL RULES FOR edit_file:\n"
            "- You MUST provide 'old_content' matching EXACTLY what is currently in the file based on the context.\n"
            "- You MUST provide 'new_content' with the replacement string.\n"
            "CRITICAL RULES FOR execute_terminal:\n"
            "- ENVIRONMENT: Operating System: Windows. Shell: CMD/Powershell. Do NOT use Linux bash syntax.\n"
            "- Do NOT use: source, chmod, apt-get, rm, /bin/.\n"
            "- Do NOT chain commands with && unless absolutely necessary.\n"
            "- You MUST provide the exact Windows-compatible shell command to run in the 'command' field.\n"
            "Example: { \"tool\": \"execute_terminal\", \"command\": \"pytest test_hello.py\" }\n\n"
            "CRITICAL RULES FOR CODE GENERATION:\n"
            "- Do NOT generate boilerplate code like `def main():` or `if __name__ == '__main__':` unless explicitly requested.\n"
            "- Only generate the exact code requested by the user, nothing more.\n\n"
            "Do NOT include markdown blocks, prose, or explanations. Only return valid JSON."
        )
        
        feedback_block = ""
        if error_feedback:
            feedback_block = (
                f"\n=== PREVIOUS ATTEMPT FAILED ===\n"
                f"File: {step_path}\n"
                f"ERROR:\n{error_feedback}\n\n"
                f"Do not repeat the same mistake. Regenerate the entire file or command correctly.\n"
            )
            
        prompt = (
            f"Task: {task_description}\nCurrent Step Action: {step_action}\nPath: {step_path}\n"
            f"{feedback_block}\n"
            f"=== WORKSPACE CONTEXT ===\n{context_text}\n\n"
            "Provide the exact tool call JSON."
        )
        
        print(f"\n--- CODER DIAGNOSTIC ---")
        print(f"Model: {model}")
        print(f"Prompt chars: {len(prompt)}, words: {len(prompt.split())}")
        print(f"System chars: {len(system_prompt)}, words: {len(system_prompt.split())}")
        print(f"--------------------------\n")
        
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
