from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path
import json

def list_files(workspace_root: str, directory: str = ".") -> ToolResult:
    try:
        safe_dir = resolve_safe_path(workspace_root, directory)
        if not safe_dir.exists() or not safe_dir.is_dir():
            return ToolResult(success=False, error=f"Directory not found: {directory}")
            
        files = [str(p.relative_to(safe_dir)) for p in safe_dir.rglob("*") if p.is_file()]
        return ToolResult(success=True, output=json.dumps(files))
    except Exception as e:
        return ToolResult(success=False, error=str(e))
