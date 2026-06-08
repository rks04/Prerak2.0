from pathlib import Path
from app.context.recent_messages import RecentMessagesProvider
from app.context.file_selector import FileSelector
from app.context.workspace_context import WorkspaceContextProvider
from app.context.token_manager import TokenManager
from app.context.formatter import Formatter

class ContextBuilder:
    """Pipeline orchestrator that assembles deterministic context."""
    def __init__(self):
        self.messages_provider = RecentMessagesProvider()
        self.workspace_provider = WorkspaceContextProvider()
        self.file_selector = FileSelector()
        self.token_manager = TokenManager(max_chars=14000)
        self.formatter = Formatter()

    def build_context(self, prompt: str, workspace_root: str) -> dict:
        # 1. Gather components
        recent_messages = self.messages_provider.get_recent_messages(limit=3)
        workspace_files = self.workspace_provider.get_files_in_root(workspace_root)
        selected_files = self.file_selector.select_files(prompt, workspace_root)
        
        # 2. Load file contents and enforce budget per file
        loaded_file_contents = {}
        total_chars = 0
        file_budget = 4000 # 4k chars per file max initially
        
        root = Path(workspace_root)
        for f in selected_files:
            try:
                content = (root / f).read_text(encoding="utf-8")
                trimmed = self.token_manager.trim_text(content, file_budget)
                loaded_file_contents[f] = trimmed
                total_chars += len(trimmed)
            except Exception:
                pass
                
        # 3. Format plain text
        full_context_text = self.formatter.format_context(
            prompt=prompt,
            recent_messages=recent_messages,
            workspace_files=workspace_files,
            loaded_file_contents=loaded_file_contents
        )
        
        # Global trim just in case
        final_context = self.token_manager.trim_text(full_context_text, self.token_manager.max_chars)
        
        # 4. Return assembled data for orchestrator and observability
        return {
            "formatted_text": final_context,
            "metadata": {
                "files_loaded": list(loaded_file_contents.keys()),
                "recent_messages_count": len(recent_messages),
                "estimated_tokens": len(final_context) // 4,
                "truncated": len(full_context_text) > self.token_manager.max_chars,
                "workspace_files_detected": len(workspace_files)
            }
        }

context_builder = ContextBuilder()
