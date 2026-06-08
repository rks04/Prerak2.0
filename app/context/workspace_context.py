import os
from pathlib import Path
from typing import List

class WorkspaceContextProvider:
    """Constructs a minimal structural representation of the workspace."""
    def get_files_in_root(self, workspace_root: str) -> List[str]:
        root = Path(workspace_root)
        if not root.exists():
            return []
            
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Ignore heavy directories
            dirnames[:] = [d for d in dirnames if d not in ['.git', '__pycache__', 'venv', 'node_modules']]
            for f in filenames:
                full_path = Path(dirpath) / f
                try:
                    rel_path = full_path.relative_to(root)
                    files.append(str(rel_path).replace("\\", "/"))
                except ValueError:
                    pass
        return files
