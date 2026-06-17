from typing import Dict, Any
from app.tools.registry import tool_registry
from app.tools.models import ToolResult

import inspect

class ToolExecutor:
    """Executes tools requested by the Coder Agent and handles errors."""
    def execute(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolResult:
        func = tool_registry.get_tool(tool_name)
        if not func:
            return ToolResult(success=False, error=f"Tool {tool_name} not found.")
        try:
            sig = inspect.signature(func)
            allowed_kwargs = { k: v for k, v in kwargs.items() if k in sig.parameters }
            return func(**allowed_kwargs)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
