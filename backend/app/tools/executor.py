from typing import Dict, Any
from app.tools.registry import tool_registry
from app.tools.models import ToolResult

class ToolExecutor:
    """Executes tools requested by the Coder Agent and handles errors."""
    def execute(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolResult:
        func = tool_registry.get_tool(tool_name)
        if not func:
            return ToolResult(success=False, error=f"Tool {tool_name} not found.")
        try:
            # We assume func returns a ToolResult directly
            return func(**kwargs)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
