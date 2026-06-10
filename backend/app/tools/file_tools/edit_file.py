from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

def edit_file(workspace_root: str, path: str, old_content: str, new_content: str) -> ToolResult:
    try:
        safe_path = resolve_safe_path(workspace_root, path)
        if not safe_path.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
            
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if not old_content:
            if not content.strip():
                # If file is empty and old_content is empty, just write new_content
                updated_content = new_content
                with open(safe_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                return ToolResult(success=True, output=f"Successfully initialized {path} with new content.")
            else:
                return ToolResult(success=False, error="old_content cannot be empty unless the file is completely empty. Provide the exact text to replace.")
            
        if old_content not in content:
            return ToolResult(success=False, error="Target content not found in file.")
            
        updated_content = content.replace(old_content, new_content)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        return ToolResult(success=True, output=f"Successfully edited {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
