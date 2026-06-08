from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

def write_file(workspace_root: str, path: str, content: str) -> ToolResult:
    try:
        safe_path = resolve_safe_path(workspace_root, path)
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return ToolResult(success=True, output=f"Successfully wrote to {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
