import os
from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

def delete_file(workspace_root: str, path: str) -> ToolResult:
    try:
        safe_path = resolve_safe_path(workspace_root, path)
        if not safe_path.exists():
            return ToolResult(success=False, error=f"File {path} does not exist.")
        if safe_path.is_dir():
            return ToolResult(success=False, error=f"{path} is a directory. Use execute_terminal to remove directories.")
        os.remove(safe_path)
        return ToolResult(success=True, output=f"Successfully deleted {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
