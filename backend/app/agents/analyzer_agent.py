import json
from app.runtime.model_router import model_router
from app.runtime.model_router import ModelRouter
from pydantic import BaseModel, Field
from typing import List

class AnalyzerOutput(BaseModel):
    category: str = Field(description="One of: dependency_conflict, syntax_error, logic_error, guard_violation, other")
    diagnosis: str = Field(description="A brief explanation of the root cause")
    recovery_sequence: List[str] = Field(description="A strict tool sequence to fix the issue")

class AnalyzerAgent:
    """The powered agent responsible for diagnosing errors and generating recovery sequences."""
    
    async def analyze(self, error_text: str, context_text: str = "") -> AnalyzerOutput:
        model = ModelRouter.get_planner_model()
        system_prompt = (
            "You are the Observation Analyzer for an autonomous AI coding agent.\n"
            "Your job is to read an error message (and workspace context) and output a precise diagnosis and recovery plan.\n"
            "You MUST output pure JSON matching exactly:\n"
            "{\n"
            "  'category': 'One of: dependency_conflict, syntax_error, logic_error, guard_violation, other',\n"
            "  'diagnosis': 'Brief explanation of the root cause',\n"
            "  'recovery_sequence': ['A list', 'of tools', 'to execute']\n"
            "}\n"
            "CRITICAL RULES:\n"
            "- If the error is a missing dependency or version conflict (e.g. ImportError), the category MUST be 'dependency_conflict' and the sequence MUST include `read_file` (to check requirements), `edit_file` (to fix requirements), and `execute_terminal` (to install).\n"
            "- If it's a syntax error, the sequence should be `read_file`, `edit_file`, `execute_terminal`, `verify_goal`, `task_completed`.\n"
            "- Do not write code. Just categorize and plan the recovery.\n"
        )
        
        prompt = f"Error to Analyze:\n{error_text}\n\nWorkspace Context:\n{context_text}"
        
        print(f"\n--- ANALYZER DIAGNOSTIC ---")
        print(f"Model: {model}")
        print(f"--------------------------\n")
        
        response = await model_router.generate(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        try:
            data = json.loads(response)
            out = AnalyzerOutput(**data)
            
            if out.category == "dependency_conflict":
                from app.execution.dependency_manager import DependencyManager
                resolution = DependencyManager.resolve_from_error(error_text)
                if resolution:
                    out.diagnosis += f"\n[DEPENDENCY MANAGER RESOLVED]: Please write the following to requirements.txt exactly:\n{resolution}"
                    out.recovery_sequence = ["write_file", "execute_terminal"]
            return out
        except Exception as e:
            raise ValueError(f"Analyzer output validation failed: {str(e)} | Output: {response}")
