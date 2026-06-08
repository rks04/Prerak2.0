import re
from pathlib import Path
from typing import List, Set
from app.context.workspace_context import WorkspaceContextProvider

class FileSelector:
    """Intelligently selects files based on prompt mentions and recency."""
    def __init__(self):
        self.workspace_provider = WorkspaceContextProvider()

    def select_files(self, prompt: str, workspace_root: str, max_files: int = 3) -> List[str]:
        selected: Set[str] = set()
        workspace_files = self.workspace_provider.get_files_in_root(workspace_root)
        
        # Priority 1: Explicit filenames in prompt
        prompt_words = re.findall(r'\b[\w\.-]+\.\w+\b', prompt)
        for word in prompt_words:
            for wf in workspace_files:
                if wf.endswith(word):
                    selected.add(wf)

        # Priority 2: Recently modified files
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
            selected.add(f)

        return list(selected)[:max_files]
