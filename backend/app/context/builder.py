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

    def build_planner_context(self, prompt: str, workspace_root: str, convo_id: str) -> dict:
        recent_messages = self.messages_provider.get_recent_messages(workspace_root=workspace_root, convo_id=convo_id, limit=3)
        workspace_files = self.workspace_provider.get_files_in_root(workspace_root)
        
        # No file reading for planner! Massive speedup.
        final_context = self.formatter.format_planner_context(
            prompt=prompt,
            recent_messages=recent_messages,
            workspace_files=workspace_files
        )
        final_context = self.token_manager.trim_text(final_context, 3000) # strict planner limit
        
        return {
            "formatted_text": final_context,
            "metadata": {
                "recent_messages_count": len(recent_messages),
                "estimated_tokens": len(final_context) // 4,
                "workspace_files_detected": len(workspace_files)
            }
        }
        
    def build_coder_context(self, prompt: str, workspace_root: str, target_path: str) -> dict:
        content = ""
        root = Path(workspace_root)
        safe_path = root / target_path
        
        if safe_path.exists() and safe_path.is_file():
            try:
                raw_content = safe_path.read_text(encoding="utf-8")
                content = self.token_manager.trim_text(raw_content, 8000) # strict coder limit per file
            except Exception:
                pass
                
        final_context = self.formatter.format_coder_context(
            prompt=prompt,
            target_path=target_path,
            content=content
        )
        
        return {
            "formatted_text": final_context,
            "metadata": {
                "target_file": target_path,
                "estimated_tokens": len(final_context) // 4
            }
        }

context_builder = ContextBuilder()
