from app.runtime.model_router import model_router
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
            "- TRUTHFULNESS: You must ONLY state that a file was modified if the execution history explicitly shows a SUCCESSFUL tool call for write_file or edit_file. If the edit failed, you must accurately report that the file was NOT modified.\n"
            "- Be concise. List the actual files that were successfully created or modified based ONLY on the evidence.\n"
            "- Provide the commands the user needs to run to start their application (if applicable).\n"
            "- Highlight the final verification evidence."
        )
        
        history_block = ""
        for i, turn in enumerate(conversation_history):
            if turn["role"] == "assistant":
                history_block += f"\n[Step {i//2 + 1}] ACTION INTENT:\n{turn['content']}\n"
            elif turn["role"] == "system":
                # truncate long outputs to save context window
                content = turn['content']
                if len(content) > 1000:
                    content = content[:1000] + "... [TRUNCATED]"
                history_block += f"[Step {i//2 + 1}] ACTUAL RESULT (Must be True):\n{content}\n"
                
        prompt = (
            f"Goal: {task_description}\n\n"
            f"=== EXECUTION HISTORY (FACTS ONLY) ===\n{history_block}\n\n"
            "Write the truthful final summary for the user based strictly on the Actual Results above."
        )
        
        try:
            response = await model_router.generate(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                json_mode=False
            )
            return response
        except Exception as e:
            return f"Task completed successfully, but summary generation failed: {str(e)}"
