from typing import Callable, Dict
from app.security.tool_permissions import ALLOWED_TOOLS

import inspect

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        if name in ALLOWED_TOOLS:
            self._tools[name] = func

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

    def get_all_tool_schemas(self) -> list[dict]:
        schemas = []
        for name, func in self._tools.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or ""
            
            params = {}
            required = []
            for param_name, param in sig.parameters.items():
                if param_name == "workspace_root":
                    continue
                
                param_type = "string"
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"
                
                params[param_name] = {
                    "type": param_type
                }
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)
                    
            schemas.append({
                "tool_name": name,
                "description": doc.split("\n")[0] if doc else f"Tool: {name}",
                "parameters": params,
                "required": required
            })
        return schemas

tool_registry = ToolRegistry()

# Register core file tools
from app.tools.file_tools.write_file import write_file
from app.tools.file_tools.read_file import read_file
from app.tools.file_tools.edit_file import edit_file
from app.tools.file_tools.delete_file import delete_file
from app.tools.workspace_tools.list_files import list_files
from app.tools.terminal_tools.execute_terminal import execute_terminal

from app.tools.workspace_tools.search_code import search_code_semantic
from app.tools.workspace_tools.search_code_exact import search_code_exact
from app.tools.models import ToolResult

def task_completed(status: str, summary: str, evidence: list[str] = []) -> ToolResult:
    """Call this tool when you have fully completed the goal OR when the goal is blocked/impossible. Status MUST be 'success', 'failed', or 'blocked'. Provide a summary and evidence."""
    return ToolResult(success=True, output=f"Task Completed [{status}]: {summary}. Evidence: {evidence}")

def verify_goal(criteria_checked: str, proof_of_success: str) -> ToolResult:
    """Call this tool to officially verify that the success criteria has been met. You must provide the exact proof (e.g. terminal output) that shows it succeeded."""
    return ToolResult(success=True, output=f"Goal verified: {criteria_checked}. Proof: {proof_of_success}")

tool_registry.register("write_file", write_file)
tool_registry.register("read_file", read_file)
tool_registry.register("edit_file", edit_file)
tool_registry.register("delete_file", delete_file)
tool_registry.register("list_files", list_files)
tool_registry.register("execute_terminal", execute_terminal)
tool_registry.register("search_code_semantic", search_code_semantic)
tool_registry.register("search_code_exact", search_code_exact)
tool_registry.register("verify_goal", verify_goal)
tool_registry.register("task_completed", task_completed)
