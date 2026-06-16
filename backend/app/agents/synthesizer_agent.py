from app.runtime.ollama_client import ollama_client
from app.runtime.model_router import ModelRouter

class SynthesizerAgent:
    """Agent responsible for translating the execution trace into a human-readable summary."""
    
    async def synthesize(self, task_description: str, conversation_history: list[dict]) -> str:
        model = ModelRouter.get_summarizer_model()
        
        system_prompt = (
            "You are the Final Synthesizer for an autonomous AI coder. "
            "Your job is to read the execution history and write a beautiful, human-readable summary of what was accomplished.\n"
            "CRITICAL RULES:\n"
            "- Do not use JSON. Output plain markdown text.\n"
            "- Be concise. List the files that were created or modified.\n"
            "- Provide the commands the user needs to run to start their application (if applicable).\n"
            "- Highlight that the success criteria was verified."
        )
        
        history_block = ""
        for i, turn in enumerate(conversation_history):
            if turn["role"] == "assistant":
                history_block += f"\n[Iteration {i//2 + 1}] TOOL CALL:\n{turn['content']}\n"
            elif turn["role"] == "system":
                # truncate long outputs to save context window
                content = turn['content']
                if len(content) > 1000:
                    content = content[:1000] + "... [TRUNCATED]"
                history_block += f"[Iteration {i//2 + 1}] RESULT:\n{content}\n"
                
        prompt = (
            f"Goal: {task_description}\n\n"
            f"=== EXECUTION HISTORY ===\n{history_block}\n\n"
            "Write the final summary for the user."
        )
        
        try:
            response = await ollama_client.generate(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                json_mode=False
            )
            return response
        except Exception as e:
            return f"Task completed successfully, but summary generation failed: {str(e)}"
