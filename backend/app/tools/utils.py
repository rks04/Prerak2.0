from pathlib import Path

def resolve_safe_path(workspace_root: str | Path, target_path: str | Path) -> Path:
    """Ensures that the resolved path does not escape the workspace root."""
    root = Path(workspace_root).resolve()
    resolved = (root / target_path).resolve()
    
    if not resolved.is_relative_to(root):
        raise PermissionError(f"Path traversal attempt: {target_path} escapes workspace {root}")
        
    return resolved
