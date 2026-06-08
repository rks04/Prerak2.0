from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

def read_file(workspace_root: str, path: str) -> ToolResult:
    try:
        safe_path = resolve_safe_path(workspace_root, path)
        if not safe_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not safe_path.is_file():
            return ToolResult(success=False, error=f"Path is not a file: {path}")
            
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return ToolResult(success=True, output=content)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
