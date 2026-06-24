import os
from app.tools.models import ToolResult
from app.tools.utils import resolve_safe_path

def search_code_exact(workspace_root: str, query: str) -> ToolResult:
    """Performs an exact string match search for text INSIDE files across the workspace. DO NOT use this to find files by filename (use list_files instead)."""
    print(f"SEARCH_CODE_EXACT: started with query '{query}'")
    try:
        root_path = resolve_safe_path(workspace_root, ".")
        results = []
        
        # Exclude common large/binary directories and execution memory
        exclude_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".prerak", ".memory", "logs", "scratch"}
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Mutate dirnames to exclude ignored directories
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
            
            for file in filenames:
                # Basic extension filter to avoid binaries
                if file.endswith((".pyc", ".zip", ".sqlite3", ".db", ".png", ".jpg", ".jpeg", ".ico")):
                    continue
                    
                file_path = os.path.join(dirpath, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            if query in line:
                                rel_path = os.path.relpath(file_path, root_path)
                                results.append(f"--- File: {rel_path} (Line {i+1}) ---\n{line.strip()}")
                except UnicodeDecodeError:
                    continue # Skip binary files that don't match extension filter
                    
        if not results:
            return ToolResult(success=True, output="No matches found.")
            
        final_output = "\n".join(results)
        
        # Cap output if it's too massive
        if len(final_output) > 5000:
            final_output = final_output[:5000] + "\n... [TRUNCATED DUE TO SIZE]"
            
        return ToolResult(success=True, output=final_output)
        
    except Exception as e:
        return ToolResult(success=False, error=str(e))
