import re
from pathlib import Path
from typing import List, Set
import os
from app.context.workspace_context import WorkspaceContextProvider

class FileSelector:
    """Intelligently selects files based on prompt mentions and recency."""
    def __init__(self):
        self.workspace_provider = WorkspaceContextProvider()

    def select_files(self, prompt: str, workspace_root: str, max_files: int = 3, recent_touched_paths: List[str] = None) -> List[str]:
        selected: List[str] = []
        
        # Priority 1: Recently modified files from DB
        if recent_touched_paths:
            for f in recent_touched_paths:
                full_path = os.path.join(workspace_root, f)
                if os.path.exists(full_path) and f not in selected:
                    selected.append(f)
                    if len(selected) >= max_files:
                        return selected

        # Priority 2: Explicit filenames in prompt
        workspace_files = self.workspace_provider.get_files_in_root(workspace_root)
        prompt_words = re.findall(r'\b[\w\.-]+\.\w+\b', prompt)
        for word in prompt_words:
            for wf in workspace_files:
                if wf.endswith(word) and wf not in selected:
                    selected.append(wf)
                    if len(selected) >= max_files:
                        return selected

        # Priority 3: Fallback to filesystem recency
        root = Path(workspace_root)
        def get_mtime(f):
            try:
                return (root / f).stat().st_mtime
            except:
                return 0

        sorted_files = sorted(workspace_files, key=get_mtime, reverse=True)
        
        for f in sorted_files:
            if len(selected) >= max_files:
                break
            if f not in selected:
                selected.append(f)

        return selected[:max_files]
