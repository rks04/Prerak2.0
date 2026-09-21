from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path
from pathlib import Path
import traceback

def write_file(workspace_root: str, path: str, content: str) -> ToolResult:
    try:
        print(f"[WRITE_FILE START] Path: {path}")
        safe_path = resolve_safe_path(workspace_root, path)
        print(f"[WRITE_FILE] Safe Path: {safe_path}")
        
        safe_path = Path(safe_path)
        print(f"[WRITE_FILE] Parent Exists: {safe_path.parent.exists()}")
        print(f"[WRITE_FILE] Target Exists: {safe_path.exists()}")
        
        print("[WRITE_FILE] Creating directories")
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        print("[WRITE_FILE] Opening file and writing")
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("[WRITE_FILE] Done")
        return ToolResult(success=True, output=f"Successfully wrote to {path}")
    except Exception as e:
        err_msg = f"Exception: {str(e)}\n{traceback.format_exc()}"
        print(f"[WRITE_FILE FAILED] {err_msg}")
        return ToolResult(success=False, error=err_msg)
