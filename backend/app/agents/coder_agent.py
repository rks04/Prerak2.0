import json
from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter
from app.models.schemas import CoderOutput

from app.tools.registry import tool_registry

class CoderAgent:
    """The powered agent responsible for writing code and making tool calls."""
    
    async def handle_task(self, task_description: str, conversation_history: list[dict], context_text: str = "") -> CoderOutput:
        model = ModelRouter.get_coder_model()
        
        tool_schemas = json.dumps(tool_registry.get_all_tool_schemas(), indent=2)
        
        system_prompt = (
            "You are a strict Coder Agent.\n"
            "You MUST output pure JSON containing ONLY the tool call.\n"
            "Format: { 'tool': '<tool_name>', '<arg_name>': '<arg_value>', ... }\n\n"
            f"AVAILABLE TOOLS:\n{tool_schemas}\n\n"
            "CRITICAL RULES:\n"
            "- ENVIRONMENT: Operating System: Windows. Shell: CMD/Powershell. Do NOT use Linux bash syntax.\n"
            "- Do NOT use: source, chmod, apt-get, rm, /bin/.\n"
            "- Do NOT chain commands with && unless absolutely necessary.\n"
            "- GOAL VERIFICATION: You MUST call `verify_goal` to prove the success criteria is met BEFORE calling `task_completed`.\n\n"
            "Do NOT include markdown blocks, prose, or explanations. Only return valid JSON."
        )
        
        history_block = ""
        for i, turn in enumerate(conversation_history):
            if turn["role"] == "assistant":
                history_block += f"\n[Iteration {i//2 + 1}] YOU CALLED TOOL:\n{turn['content']}\n"
            elif turn["role"] == "system":
                history_block += f"[Iteration {i//2 + 1}] TOOL RESULT:\n{turn['content']}\n"
                
        prompt = (
            f"Goal: {task_description}\n\n"
            f"=== WORKSPACE CONTEXT ===\n{context_text}\n\n"
            f"=== EXECUTION HISTORY ===\n{history_block if history_block else 'No tools called yet.'}\n\n"
            "Analyze the history and workspace context. Decide the next step. Provide the exact tool call JSON."
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
