from app.tools.models import ToolResult
from app.execution.process_manager import process_manager

def tail_process_logs(process_id: str, lines: int = 20) -> ToolResult:
    """Tails the stdout and stderr of a background process by its process_id. This is useful for inspecting running services without restarting them."""
    logs = process_manager.tail_logs(process_id, lines)
    if "not found" in logs:
        return ToolResult(success=False, error=logs)
    return ToolResult(success=True, output=logs)
