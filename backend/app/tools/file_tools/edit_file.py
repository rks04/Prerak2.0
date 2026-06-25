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
                return ToolResult(success=False, error="ERROR: old_content cannot be empty. You MUST perfectly match existing text from the file. Use read_file to see the exact text first.")
            
        if old_content not in content:
            # Fallback: LLMs sometimes mistakenly add a trailing newline to old_content
            if old_content.endswith('\n') and old_content[:-1] in content:
                old_content = old_content[:-1]
                if new_content.endswith('\n'):
                    new_content = new_content[:-1]
            else:
                return ToolResult(success=False, error="Target content not found in file. Ensure you are not appending artificial newlines (\\n) that don't exist in the file.")
                
        updated_content = content.replace(old_content, new_content)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
            
        return ToolResult(success=True, output=f"Successfully edited {path}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))
