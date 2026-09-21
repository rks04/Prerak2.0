import json
from app.runtime.model_router import model_router
from app.runtime.model_router import ModelRouter
from pydantic import BaseModel
from typing import Optional

class ObserverOutput(BaseModel):
    execution: str
    severity: str
    verification: str
    evidence: dict
    feedback: str

class ObserverAgent:
    """The agent responsible for interpreting tool execution results and generating structured evidence."""
    
    async def observe(self, tool_name: str, tool_kwargs: dict, output: str, error: str, expected_success_conditions: list) -> ObserverOutput:
        model = ModelRouter.get_planner_model()
        
        system_prompt = (
            "You are the strict Observer Agent for an autonomous coding pipeline.\n"
            "Your job is to read the raw output and error from a tool execution, evaluate it against the expected success conditions, and classify the result.\n"
            "You MUST output pure JSON matching this schema:\n"
            "{\n"
            "  'execution': 'SUCCESS, SERVER_READY, HTTP_READY, READY, VERIFIED, PARTIAL, RECOVERABLE, FAILURE, FATAL, BLOCKED, LONG_RUNNING, or SCHEMA_VIOLATION',\n"
            "  'severity': 'RECOVERABLE, FATAL, or NONE',\n"
            "  'verification': 'VERIFIED, UNVERIFIED, or NA',\n"
            "  'evidence': {'tool': '...', 'matched': '...', 'command': '...', 'exit_code': 0},\n"
            "  'feedback': 'Concise interpretation of the result.'\n"
            "}\n"
            "CRITICAL RULES:\n"
            "- 'execution' = SUCCESS if the tool ran properly and achieved its goal. LONG_RUNNING if it's a background server that started successfully.\n"
            "- 'execution' = SCHEMA_VIOLATION if the tool failed because of an invalid argument, missing parameter, or enum mismatch.\n"
            "- 'execution' = SERVER_READY if a background process is confirmed to be running AND successfully serving requests.\n"
            "- 'verification' = VERIFIED ONLY if the tool output explicitly proves the 'Expected Success Conditions' were met. Otherwise UNVERIFIED. If it's just a file write, use NA.\n"
            "- HTTP SEMANTICS: For `http_request` results:\n"
            "  - 200, 201, 204 -> VERIFIED\n"
            "  - 400, 401, 403, 404, 409 -> UNVERIFIED\n"
            "  - 500, timeout, connection_refused -> RECOVERABLE (with execution=FAILURE)\n"
            "- FILE VERIFICATION: When evaluating `list_files` against `Expected Success Conditions` (e.g. required files), you MUST cross-reference the output. If ANY expected file is missing, you MUST emit execution=FAILURE and verification=UNVERIFIED.\n"
            "- Never hallucinate success. If there's an error, mark FAILURE.\n"
        )
        
        prompt = (
            f"Tool Executed: {tool_name}\n"
            f"Arguments: {json.dumps(tool_kwargs)}\n"
            f"Expected Success Conditions: {expected_success_conditions}\n\n"
            f"--- OUTPUT ---\n{output[:1000]}\n"
            f"--- ERROR ---\n{error[:1000]}\n\n"
            "Classify this execution."
        )
        
        response = await model_router.generate(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            json_mode=True
        )
        
        try:
            data = json.loads(response)
            return ObserverOutput(**data)
        except Exception as e:
            raise ValueError(f"Observer output validation failed: {str(e)} | Output: {response}")
